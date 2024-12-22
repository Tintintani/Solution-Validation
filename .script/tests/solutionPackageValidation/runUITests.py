import json
import os
import requests
import subprocess
from dotenv import load_dotenv
import time
import random

load_dotenv()


testimBaseUrl = "https://api.testim.io"
workspaceBaseUrl = "https://portal.azure.com/?l=en.en-us#view/Microsoft_Azure_Security_Insights/MainMenuBlade/~/NewsAndGuides/id/%2Fsubscriptions%2F9023f5b5-df22-4313-8fbf-b4b75af8a6d9%2Fresourcegroups%2Fe2e-solutionintegration-testim-rg%2Fproviders%2Fmicrosoft.securityinsightsarg%2Fsentinel%2Fe2e-solutionintegration-testim-sentinelworkspace"
branch = "users/tanishqarora/solutionIntegrationTesting"
grid = "SENTINEL - GRID"
config = "Sentinel-Default"
testLabels = ["Test"]

contentTypes = ["dataConnector", "parser", "analyticsRule", "huntingQuery", "workbook", "playbook", "watchlist"]

testIds = {
    "metadataInstallDelete": "MYLFAf0eyYRUwXnu",
    "dataConnector": "cpYyS88vLGVPqhuo",
    "parser": "yY8j93ZdSu25tJOx",
    "analyticsRule": "oJQumpUe9Gtz6ttV",
    "huntingQuery": "S7F3UiGSdxLnjfhg",
    "workbook": "Oy8TvgoOdGMUZy7U",
    "playbook": "whBf8pokFQX1DxGC",
    "watchlist": "j5JkBA7TR0GFfxAE"
}

# Azure Access Token
def getAccessToken():
    # Get an access token using Azure CLI
    result = subprocess.run('az account get-access-token --output json', capture_output=True, shell=True)
    result = json.loads(result.stdout)
    return result['accessToken'], result['expires_on']

# Run Testim Test
def runTestimTest(testId, testData, apiKey):

    testData.update({"username": os.environ.get('USERNAME')})
    testData.update({"password": os.environ.get('PASSWORD')})
    
    url = f"{testimBaseUrl}/tests/run/{testId}"

    headers = {
        'Authorization': f'Bearer {apiKey}',
        'Content-Type': 'application/json'
    }

    payload = {
        "baseUrl": workspaceBaseUrl,
        "branch": branch,
        "grid": grid,
        "parallel": 1,
        "params": testData,
        "resultLabels": testLabels,
        "retries": 0,
        "testConfig": config,
        "timeout": 600,
        "turboMode": True
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error while Running Test: {e}")
        raise
    
    return response.json()['executionId']

# Get Execution Result
def getExectutionResult(executionId, apiKey):
    url = f"{testimBaseUrl}/v2/runs/executions/{executionId}"

    headers = {
        'Authorization': f'Bearer {apiKey}',
        'Content-Type': 'application/json'
    }

    while(True):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()  

            if ('status' in data['execution'] and data['execution']['status'] == 'RUNNING'):
                time.sleep(180)
                continue
            elif (data['execution']['executionResult'] == 'Passed'):
                return [data['execution']['tests'][0]['executionStatus']]
            elif (data['execution']['executionResult'] == 'Failed'):
                return [data['execution']['tests'][0]['executionStatus'], data['execution']['tests'][0]['errorMessage']]
            else:
                continue

        except requests.exceptions.RequestException as e:
            print(f"Error while Getting Execution Result: {e}")
            raise

# Delete the deployed resources
def deleteResources():
    count = 0

    accessToken, tokenExpiresOn = getAccessToken()

    with open("outputResources.json", 'r', encoding='utf-8') as file:
        resources = json.load(file)
        file.close()
    
    for resource in resources:
        
        url = f"https://management.azure.com{resource['id']}?api-version=2024-09-01"

        headers = {
            'Authorization': f'Bearer {accessToken}',   
            'Content-Type': 'application/json'
        }

        attempts = 0
        while attempts < 5:
            attempts += 1

            if time.time() > tokenExpiresOn:
                accessToken, tokenExpiresOn = getAccessToken()
                
            try:
                response = requests.delete(url, headers=headers)
                response.raise_for_status()
            
                print(f"Deleted {resource['id']}")
                count += 1
                break

            except requests.exceptions.RequestException as e:
                print(f"Error: {e}. Retrying in 5 seconds...")
        else:
            print(f"Failed to delete resource with resourceId: {resource['id']} after maximum attempts.")
            
        time.sleep(2)

    print(f"Deleted {count} resources, total {len(resources)}\n")

# Run Metadata Install Delete Test
def metadataInstallDeleteTest(metadata, executionResult, apiKey):

    try:
        executionId = runTestimTest(testIds['metadataInstallDelete'], metadata, apiKey)
    except requests.exceptions.RequestException:
        raise

    try:
        result = getExectutionResult(executionId, apiKey)
    except requests.exceptions.RequestException:
        raise

    if(len(result) == 1):
        executionResult.append(f"Metadata Install Delete: {result[0]}")
    else:
        executionResult.append(f"Metadata Install Delete: {result[0]} - {result[1]}")

# Run Individual Content Test
def contentTest(contentType, contents, executionIds, apiKey):
    selectedContents = random.sample(contents, k=min(3, len(contents)))
    for content in selectedContents:
        try:
            executionId = runTestimTest(testIds[contentType], content, apiKey)
        except requests.exceptions.RequestException:
            raise
        executionIds.append({
            "contentType": contentType,
            "name": content['displayName'],
            "executionId": executionId
        })

# Main Function
def main():
    subscriptionId = os.environ.get('SUBSCRIPTION_ID')
    resourceGroup = os.environ.get('RESOURCE_GROUP')
    workspaceName = os.environ.get('API_VERSION')
    apiVersion = os.environ.get("SUBSCRIPTION_ID")
    apiKey = os.environ.get("TESTIM_API_KEY")

    with open(".\\templates\\solution.json", 'r', encoding='utf-8') as file:
        solution = json.load(file)
        file.close()

    executionResult = []
    executionIds = []

    for contentType in contentTypes:
        try:
            contentTest(contentType, solution[contentType], executionIds, apiKey)
        except requests.exceptions.RequestException:
            return

    # Delete the deployed content
    deleteResources()

    try:
        metadataInstallDeleteTest(solution['Metadata'], executionResult, apiKey)
    except requests.exceptions.RequestException:
        return
        

    print(executionIds)
    print('\n')
    print(executionResult)

if __name__ == "__main__":
    main()
