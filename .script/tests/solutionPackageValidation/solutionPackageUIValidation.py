import re
import json
import requests
import time
import subprocess
import os
from dotenv import load_dotenv


RepoUrl = "https://github.com/Tintintani/Solution-Validation"

############################################################################################################
# Evaluate ARM Expressions


# Azure Access Token
def getAccessToken():
    # Get an access token using Azure CLI
    result = subprocess.run('az account get-access-token --output json', capture_output=True, shell=True)
    result = json.loads(result.stdout)
    return result['accessToken'], result['expires_on']

# Deploy the ARM Template
def deployTemplate(subscriptionId, resourceGroup, deploymentName, templateFile, accessToken, tokenExpiresOn):

    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/{resourceGroup}/providers/Microsoft.Resources/deployments/{deploymentName}?api-version=2024-03-01"

    payload = {
        "properties": {
            "mode": "Incremental",
            "template": templateFile,
        }
    }

    headers = {
        'Authorization': f'Bearer {accessToken}',
        'Content-Type': 'application/json'
    }

    if time.time() > tokenExpiresOn:
        accessToken, tokenExpiresOn = getAccessToken()

    try:
        response = requests.put(url, headers=headers, data = json.dumps(payload))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Deployment Error: {e}\n")
        raise

# List of Deployed Resources
def getResources(subscriptionId, resourceGroup, deploymentName, accessToken, tokenExpiresOn):
    
    url = f"https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/{resourceGroup}/providers/Microsoft.Resources/deployments/{deploymentName}/?api-version=2024-03-01"

    headers = {
        'Authorization': f'Bearer {accessToken}',
        'Content-Type': 'application/json'
    }
    attempts = 0
    
    while attempts < 10:
        attempts += 1
        try:

            if time.time() > tokenExpiresOn:
                accessToken, tokenExpiresOn = getAccessToken()

            # response = requests.get(url, headers=headers, timeout=(10, 60))
            response = requests.get(url, headers=headers, timeout=(10, 60))
            response.raise_for_status()
            data = response.json()
            
            print(f"Deployment Current State: {data['properties']['provisioningState']}")
            
            if (data['properties']['provisioningState'] == 'Succeeded'):
                print(f"Deployment Succeeded: Deployed {len(data['properties']['outputResources'])} resources\n")
                return data['properties']['outputResources']
                
                            
            print(f"Status {response.status_code}. Retrying in 5 seconds...\n")
            time.sleep(5)
        
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            raise

        except requests.exceptions.Timeout as e:
            print(f"Timeout Error: {e}")
            raise TimeoutError

# Export evaluated ARM Template for each resource
def getTemplate(resources, accessToken, tokenExpiresOn):

    exportedTemplated = []
    count = 0

    for resource in resources:

        url = f"https://management.azure.com{resource['id']}?api-version=2024-09-01"

        headers = {
            'Authorization': f'Bearer {accessToken}',
            'Content-Type': 'application/json'
        }

        try:
            if time.time() > tokenExpiresOn:
                accessToken, tokenExpiresOn = getAccessToken()

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            print(f"Exported Template for {resource['id']}")
            exportedTemplated.append(response.json())
            count += 1
        
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            raise

        time.sleep(2)

    print(f"Exported {count} templates, total resource {len(resources)}\n")

    return exportedTemplated

# Delete the deployed resources
def deleteResources(resources, accessToken, tokenExpiresOn):
    count = 0

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

# Evaluate ARM Expressions in the mainTemplate.json file
def evaluateARMExpressions(templateFile):

    templateFile['parameters']['workspace']['defaultValue'] = os.environ.get('WORKSPACE_NAME')

    subscriptionId = os.environ.get('SUBSCRIPTION_ID')
    resrouceGroup = os.environ.get('RESOURCE_GROUP')
    deploymentName = "TestDeployment"
    accessToken, expiresOn = getAccessToken()

    # Deploy the Template
    try:
        deployTemplate(subscriptionId, resrouceGroup, deploymentName, templateFile, accessToken, expiresOn)
    except requests.exceptions.RequestException:
        return
    
    # Get the list of deployed resources
    try:
        outputResources = getResources(subscriptionId, resrouceGroup, deploymentName, accessToken, expiresOn)
    except (requests.exceptions.RequestException, TimeoutError):
        return
    
    # Filter out the contentTemplates andand Watchlists
    regex = re.compile(r'.*(contentTemplates|andWatchlists|contentPackages).*')
    outputResources = [resource for resource in outputResources if regex.match(resource['id'])]

    with open("outputResources.json", 'w', encoding='utf-8') as file:
        json.dump(outputResources, file, indent=4)


    # Get the templates of the deployed content
    try:
        exportedTemplates = getTemplate(outputResources, accessToken, expiresOn)
    except requests.exceptions.RequestException:
        return

    with open("exportedTemplates.json", 'w', encoding='utf-8') as file:
        json.dump(exportedTemplates, file, indent=4)  

    # Delete the deployed content
    deleteResources(outputResources, accessToken, expiresOn)

    return exportedTemplates


############################################################################################################
# Extract Information

# Function to remove HTML tags
def removeHtmlTags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# Function to remove unwanted characters and text
def cleanText(text):
    text = removeHtmlTags(text)
    # text = re.sub(r'\n\s\d+.\s', '', text)  # Remove \n
    text = re.sub(r'^\d+\.\s', '', text)  # Remove numbers at the beginning of the text
    text = re.sub(r'\n*\s+\d+\.\s', '', text)  # Remove numbers at the beginning of the text
    text = re.sub(r'\s*\n+', '', text)  # Remove spaces before and after \n characters
    text = re.sub(r'\*+\s*', '', text)  # Remove ** for bold
    text = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', text)  # Keep text within square brackets, remove hyperlinks
    text = text.replace('\n', '')  # Remove \n
    text = text.replace('&amp;', '&')  # Replace &amp; with &
    return text


def multipleElements(list):
    newList = list
    newList.insert(1, str(len(newList) - 1) + '') if len(newList) > 1 else newList
    return newList

# Function to add space between camel case
def addSpace(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    return text

# Function to get Query
def getQuery(text):
    text = text.replace('\n', '')
    return text

# Function to get Time Period
def getTimePeriod(text):

    # Define patterns for ISO 8601 durations
    patterns = {
        r'P(\d+)D': r'\1 day',  # Days
        r'PT(\d+)H': r'\1 hour',  # Hours
        r'PT(\d+)M': r'\1 minute'  # Minutes
    }

    # Apply patterns to the text
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text)
    
    
    # Conversion
    text = re.sub(r'(\d+)\s(hour)', lambda m: f"{int(m.group(1)) // 24} day" if int(m.group(1)) % 24 == 0 else m.group(0), text)
    text = re.sub(r'(\d+)\s(minute)', lambda m: f"{int(m.group(1)) // 60} hour" if int(m.group(1)) % 60 == 0 else m.group(0), text)
    
    
    # Handle pluralization
    text = re.sub(r'(\d+)\s(day|hour|minute)', lambda m: f"{m.group(1)} {m.group(2)}s" if int(m.group(1)) > 1 else m.group(0), text)
    return text

# Function to get Threshold    
def getThreshold(threshold, operator):
    patterns = {
        'GreaterThan': 'more than',
        'FewerThan': 'less than',
        'Equal': 'exactly',
        'NotEqual': ''
    }
    return patterns[operator] + ' ' + str(threshold)

# Function to extract content types and their count
def extractContentType(text):
    contents = {}
    correspondingName = {
    "DataConnector" : "Data connector",
    "Parser" : "Parser",
    "Workbook" : "Workbook",
    "AnalyticsRule" : "Analytics rule",
    "HuntingQuery" : "Hunting query",
    "LogicAppsCustomConnector" : "Custom Azure Logic Apps Connectors",
    "Playbook" : "Playbook",
    "Watchlist" : "Watchlist"
    }
    for content in text:
        kind = content['kind']
        if kind in correspondingName:
            if correspondingName[kind] in contents:
                contents[correspondingName[kind]] += 1
            else:
                contents[correspondingName[kind]] = 1
    return contents

# Function to get Entity
def getEntity(entity):
    entities = {
        "account" : "Account",
        "host" : "Host",
        "ip" : "IP",
        "url": "URL",
        "azure resource" : "Azure Resource",
        "cloud application" : "Cloud Application",
        "dns resolution" : "DNS Resolution",
        "file" : "File",
        "filehash" : "FileHash",
        "process" : "Process",
        "malware" : "Malware",
        "registry key" : "Registry Key",
        "registry value" : "Registry Value",
        "security group" : "Security Group",
        "mailbox" : "Mailbox",
        "mail cluster" : "Mail Cluster",
        "mail message" : "Mail Message",
        "submission mail" : "Submission Mail",
    }

    return entities[entity.lower()]

# Function to add Content Page Description
def addContentPageDescription(createUiDefinitionFilePath):

    data = {}

    with open (createUiDefinitionFilePath, 'r', encoding='utf-8') as file:
        createUiDefinitionFile = file.read()
    file.close()
    
    parserCreateUiDefinitionFile = json.loads(createUiDefinitionFile)
    data.update({"contentPageDescription": cleanText(parserCreateUiDefinitionFile['parameters']['config']['basics']['description'])})

    return data

# Function to get the metadata of the solution
def addMetadata(mainTemplateFilePath, createUiDefinitionFilePath):
    with open(mainTemplateFilePath, 'r', encoding='utf-8') as file:
        mainTemplateFile = json.load(file)

    content = {}

    for resource in mainTemplateFile['resources']:
        if resource['type'] == 'Microsoft.OperationalInsights/workspaces/providers/contentPackages':
            content = resource['properties']
            break

    data = {}

    # Basic Metadata
    data.update({"searchKey": content['displayName']})
    data.update({"solutionName": content['source']['name']})
    data.update({"displayName": content['displayName']})
    data.update({"contentSource": content['source']['kind']})
    data.update({"sourceName": content['source']['name']})
    data.update({"provider": ', '.join(content['providers'])})
    data.update({"author": content['author']['name']})
    data.update({"bladeSupportName": 'Microsoft' if content['support']['name'] == "Microsoft Corporation" else content['support']['name']})
    data.update({"supportName": content['support']['name']})
    data.update({"category": ', '.join(sorted(content['categories']['domains']))})
    data.update({"version": content['version']})
    data.update({"bladeDescription": cleanText(content['descriptionHtml'])})
    
    # Add Content Page Description
    data.update(addContentPageDescription(createUiDefinitionFilePath))

    # parameters.update({"contentCount": ', '.join([f"{contentType}: {count}" for contentType, count in sorted(extractContentType(solution['dependencies']['criteria']).items(), key = lambda item: getCustomSortingIndex(item[0]))])})
    
    # Content Type and their Count
    data.update({"contentType" : ''.join([f"{count}{contentType}" for contentType, count in sorted(extractContentType(content['dependencies']['criteria']).items()) if contentType != "Custom Azure Logic Apps Connectors"])})

    # Total Content Count
    data.update({"contentCount":  sum(count for contentType, count in extractContentType(content['dependencies']['criteria']).items() if contentType != "Custom Azure Logic Apps Connectors" and contentType != "Watchlist")})

    # Icons
    data.update({"solutionIcon": content['icon']})
    data.update({'versionIcon' : "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTAgMi42NTYyNUgxMS45ODc1VjkuNjA1NzRDMTEuOTg3NSA5LjcxNjI4IDExLjk0NTMgOS44MjIyOSAxMS44NzAxIDkuOTAwNDRDMTEuNzk1IDkuOTc4NiAxMS42OTMgMTAuMDIyNSAxMS41ODY4IDEwLjAyMjVIMC40MDA3NUMwLjI5NDQ2NCAxMC4wMjI1IDAuMTkyNTMyIDkuOTc4NiAwLjExNzM3NyA5LjkwMDQ0QzAuMDQyMjIxOCA5LjgyMjI5IDAgOS43MTYyOCAwIDkuNjA1NzRWMi42NTYyNVoiIGZpbGw9InVybCgjcGFpbnQwX2xpbmVhcikiLz4KPHBhdGggZD0iTTAuNDAyNSAzLjk3NDAzZS0wNkgxMS41ODI0QzExLjY4ODcgMy45NzQwM2UtMDYgMTEuNzkwNiAwLjA0MzkxMzUgMTEuODY1NyAwLjEyMjA3M0MxMS45NDA5IDAuMjAwMjMyIDExLjk4MzEgMC4zMDYyMzkgMTEuOTgzMSAwLjQxNjc3NFYyLjY1NjIzSDBWMC40MTY3NzRDLTUuMDMxNjdlLTA3IDAuMzYxODg5IDAuMDEwNDIyOSAwLjMwNzU0NSAwLjAzMDY3MTggMC4yNTY4NjFDMC4wNTA5MjA3IDAuMjA2MTc3IDAuMDgwNTk2NCAwLjE2MDE1MiAwLjExNzk5NSAwLjEyMTQyOEMwLjE1NTM5NCAwLjA4MjcwMzEgMC4xOTk3NzkgMC4wNTIwNDIyIDAuMjQ4NjAyIDAuMDMxMjA0OUMwLjI5NzQyNiAwLjAxMDM2NzYgMC4zNDk3MjYgLTAuMDAwMjM1Njk2IDAuNDAyNSAzLjk3NDAzZS0wNloiIGZpbGw9IiMwMDc4RDQiLz4KPHBhdGggZD0iTTIuMDEyNyA2LjYzMzc5SDE0LjAwMDJWMTMuNTgzM0MxNC4wMDAyIDEzLjY5MzggMTMuOTU4IDEzLjc5OTggMTMuODgyOCAxMy44NzhDMTMuODA3NyAxMy45NTYxIDEzLjcwNTcgMTQuMDAwMSAxMy41OTk0IDE0LjAwMDFIMi40MTUyQzIuMzA4OTEgMTQuMDAwMSAyLjIwNjk4IDEzLjk1NjEgMi4xMzE4MiAxMy44NzhDMi4wNTY2NyAxMy43OTk4IDIuMDE0NDUgMTMuNjkzOCAyLjAxNDQ1IDEzLjU4MzNWNi42MzM3OUgyLjAxMjdaIiBmaWxsPSJ1cmwoI3BhaW50MV9saW5lYXIpIi8+CjxwYXRoIGQ9Ik0yLjQxNzgyIDMuOTczNjZIMTMuNTk3N0MxMy42NTA0IDMuOTczNDIgMTMuNzAyNiAzLjk4Mzk5IDEzLjc1MTQgNC4wMDQ3N0MxMy44MDAyIDQuMDI1NTUgMTMuODQ0NSA0LjA1NjEzIDEzLjg4MTkgNC4wOTQ3NkMxMy45MTkzIDQuMTMzMzkgMTMuOTQ5IDQuMTc5MzEgMTMuOTY5MyA0LjIyOTg4QzEzLjk4OTYgNC4yODA0NiAxNC4wMDAxIDQuMzM0NzEgMTQuMDAwMiA0LjM4OTUyVjYuNjMzNTJIMi4wMTI3VjQuMzg5NTJDMi4wMTI4MSA0LjMzNDQ4IDIuMDIzNCA0LjI4MDAxIDIuMDQzODcgNC4yMjkyNUMyLjA2NDMzIDQuMTc4NDkgMi4wOTQyNiA0LjEzMjQ1IDIuMTMxOTMgNC4wOTM3OUMyLjE2OTU5IDQuMDU1MTIgMi4yMTQyNSA0LjAyNDYgMi4yNjMzMiA0LjAwMzk4QzIuMzEyMzkgMy45ODMzNiAyLjM2NDkgMy45NzMwNiAyLjQxNzgyIDMuOTczNjZaIiBmaWxsPSIjMTk4QUIzIi8+CjxkZWZzPgo8bGluZWFyR3JhZGllbnQgaWQ9InBhaW50MF9saW5lYXIiIHgxPSI1Ljk5Mjg4IiB5MT0iMTAuMDIxNiIgeDI9IjUuOTkyODgiIHkyPSIyLjY1NjI1IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+CjxzdG9wIHN0b3AtY29sb3I9IiMwMDc4RDQiLz4KPHN0b3Agb2Zmc2V0PSIwLjUwMiIgc3RvcC1jb2xvcj0iIzQwOTNFNiIvPgo8c3RvcCBvZmZzZXQ9IjAuNzc1IiBzdG9wLWNvbG9yPSIjNUVBMEVGIi8+CjwvbGluZWFyR3JhZGllbnQ+CjxsaW5lYXJHcmFkaWVudCBpZD0icGFpbnQxX2xpbmVhciIgeDE9IjguMDA3MzIiIHkxPSIxMy45OTU1IiB4Mj0iOC4wMDczMiIgeTI9IjYuNjI5MjQiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KPHN0b3Agc3RvcC1jb2xvcj0iIzMyQkVERCIvPgo8c3RvcCBvZmZzZXQ9IjAuMTc1IiBzdG9wLWNvbG9yPSIjMzJDQUVBIi8+CjxzdG9wIG9mZnNldD0iMC40MSIgc3RvcC1jb2xvcj0iIzMyRDJGMiIvPgo8c3RvcCBvZmZzZXQ9IjAuNzc1IiBzdG9wLWNvbG9yPSIjMzJENEY1Ii8+CjwvbGluZWFyR3JhZGllbnQ+CjwvZGVmcz4KPC9zdmc+Cg=="})

    return data

# Function to add Data Connectors
def addDataConnector(content, dataConnectorMapping):
    resource = content['mainTemplate']['resources'][0]
    metadata = content['mainTemplate']['resources'][1]['properties']
    
    graphQueriesTableName = resource['properties']['connectorUiConfig']['graphQueriesTableName'] if "graphQueriesTableName" in resource['properties']['connectorUiConfig'] else ''

    dataConnector = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resource['properties']['connectorUiConfig']['descriptionMarkdown']),
        "kind": metadata['kind'],
        
        "dataTypes" : ''.join([(graphQueriesTableName if dataType['name'] == "{{graphQueriesTableName}}" else dataType['name'])+ ' --' for dataType in resource['properties']['connectorUiConfig']['dataTypes']]),
        
        "provider": resource['properties']['connectorUiConfig']['publisher'],
        "version": metadata['version'],
        "source": metadata['source']['name'],
        "author": metadata['author']['name'],
        "support": metadata['support']['name'],
    }

    dataConnectorMapping.update({content['contentId'].lower() : content['displayName']})

    return dataConnector

# Function to add Analytics Rules
def addAnalyticsRule(content, dataConnectorMapping):
    resource = content['mainTemplate']['resources'][0]
    metadata = content['mainTemplate']['resources'][1]['properties']

    dataConnectorId = []
    dataConnectorName = []
    dataTypes = set()
        
    for dataConnector in resource['properties']['requiredDataConnectors']:
        dataConnectorId.append(dataConnector['connectorId'])
        dataConnectorName.append(dataConnectorMapping[dataConnector['connectorId'].lower()])
        for dataType in dataConnector['dataTypes']:
            dataTypes.add(dataType + ' --')

    analyticsRule = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resource['properties']['description']),
        "kind": metadata['kind'],
        
        "ruleType" : resource['kind'],
        "severity": resource['properties']['severity'],
        
        "query": getQuery(resource['properties']['query']),

        "ruleFrequency": getTimePeriod(resource['properties']['queryFrequency']) if 'queryFrequency' in resource['properties'] else '' ,
        "rulePeriod": getTimePeriod(resource['properties']['queryPeriod']) if 'queryPeriod' in resource['properties'] else '',
        "suppressionDuration": getTimePeriod(resource['properties']['suppressionDuration']) if 'suppressionDuration' in resource['properties'] else '',
        'thresholdTrigger': getThreshold(resource['properties']['triggerThreshold'], resource['properties']['triggerOperator']) if 'triggerThreshold' in resource['properties'] else '',

        "tactics": [addSpace(technique) for technique in resource['properties']['tactics']] if 'tactics' in resource['properties'] else [],
        "tacticsMultiple": ''.join(multipleElements([addSpace(technique) for technique in resource['properties']['tactics']])) if 'tactics' in resource['properties'] else [],
        "techniques": resource['properties']['techniques'] if 'techniques' in resource['properties'] else [],
        "techniquesMultiple": ''.join(multipleElements([element for element in resource['properties']['techniques']])) if 'techniques' in resource['properties'] else [],
        "subTechniques": resource['properties']['subTechniques'] if 'subTechniques' in resource['properties'] else [],
        "subTechniquesMultiple": ''.join(multipleElements([element for element in resource['properties']['subTechniques']])) if 'subTechniques' in resource['properties'] else [],
        "entityMapping": resource['properties']['entityMappings'] if 'entityMappings' in resource['properties'] else [],

        "dataConnectorId" : dataConnectorId[0],
        "dataConnectorName" : dataConnectorName[0],
        "dataTypes" : ''.join(dataTypes),

        "version": metadata['version'],
        "source": metadata['source']['name'],
        "author": metadata['author']['name'],
        "support": metadata['support']['name'],
    }

    return analyticsRule
    
# Function to add Hunting Queries
def addHuntingQuery(content):
    resource = content['mainTemplate']['resources'][0]
    metadata = content['mainTemplate']['resources'][1]['properties']

    tactics = []
    techniques = []
    for tag in resource['properties']['tags']:
        if tag['name'] == 'tactics':
            tactics.append(addSpace(tag['value']))
        elif tag['name'] == 'techniques':
            techniques.append(tag['value'])

    huntingQuery = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resource['properties']['tags'][0]['value'] if resource['properties']['tags'][0]['name'] == 'description' else ''),
        "kind": metadata['kind'],

        "query": getQuery(resource['properties']['query']),

        "tactics": tactics,
        "techniques": techniques,

        "version": metadata['version'],
        "source": metadata['source']['name'],
        "author": metadata['author']['name'],
        "support": metadata['support']['name'],
    }

    return huntingQuery

# Function to add Workbooks
def addWorkbook(content):
    resources = content['mainTemplate']['resources']
    metadata = content['mainTemplate']['resources'][1]['properties']

    workbook = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(resources[0]['metadata']['description']),
        "kind": metadata['kind'],

        "dataTypes": ''.join([dataType['contentId'] + ' --' for dataType in resources[-1]['properties']['dependencies']['criteria'] if dataType["kind"] == "DataType"] if 'dependencies' in resources[-1]['properties'] else '',),
        "dataConnectorId": ' '.join([dataConnector['contentId'] for dataConnector in resources[-1]['properties']['dependencies']['criteria'] if dataConnector["kind"] == "DataConnector"] if 'dependencies' in resources[-1]['properties'] else []),
        
        "version": metadata['version'],
        "source": metadata['source']['name'],
        "author": metadata['author']['name'],
        "support": metadata['support']['name'],
    }

    return workbook

# Function to add Parsers
def addParser(content):
    resource = content['mainTemplate']['resources'][0]
    metadata = content['mainTemplate']['resources'][1]['properties']

    parser = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "kind": metadata['kind'],

        "functionAlias" : resource['properties']['functionAlias'],
        "query": getQuery(resource['properties']['query']),

        "version": metadata['version'],
        "source": metadata['source']['name'],
        "author": metadata['author']['name'],
        "support": metadata['support']['name'],
    }

    return parser

# Funtion to add Playbooks
def addPlaybook(content):
    metadata = content['mainTemplate']['metadata']

    if 'entities' in metadata:
        metadata['entities'] = [getEntity(entity) for entity in metadata['entities']]
        metadata['entities'] = multipleElements(metadata['entities'])

    
    playbook = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(metadata['description']),
        "kind": content['mainTemplate']['resources'][-1]['properties']['kind'],
        
        "prerequisites": ''.join([cleanText(prerequisite) for prerequisite in metadata['prerequisites']]),
        "postDeployment" : ''.join(cleanText(postDeployment) for postDeployment in metadata['postDeployment']) if 'postDeployment' in metadata else '',
        "entities": metadata['entities'] if 'entities' in metadata else [],
        "entitiesMultiple": ''.join(metadata['entities']) if 'entities' in metadata else '',
        "tags": ''.join(metadata['tags']) if 'tags' in metadata else '',

        "version": content['mainTemplate']['resources'][-1]['properties']['version'],
        "source": content['mainTemplate']['resources'][-1]['properties']['source']['name'],
        "author": content['mainTemplate']['resources'][-1]['properties']['author']['name'],
        "support": content['mainTemplate']['resources'][-1]['properties']['support']['name'],
    }

    return playbook

# Function to add Logic Apps
def addLogicAppsCustomConnector(content):
    logicAppsCustomConnector = {
        "searchKey" : content['contentId'],
        "displayName": content['displayName'],
        "description": cleanText(content['mainTemplate']['resources'][0]['properties']['description']),
        "version": content['version'],
    }

    return logicAppsCustomConnector

# Function to add Watchlist
def addWatchlist(content):
    watchlist = {
        "displayName": content['displayName'],
        "description": cleanText(content['description']),
        "kind": "Watchlists",
        "source" : content['source'],
        "alias" : content['watchlistAlias'],
        "provider": content['provider'],

        "itemsSearchKey": content['itemsSearchKey'],
    }

    return watchlist

# Sort to make dataConnector first
def sortContents(content):
        if 'contentKind' in content['properties'] and content['properties']['contentKind'] == 'DataConnector':
            return (0, content['properties']['contentKind'])
        return (1, content['properties']['contentKind'] if 'contentKind' in content['properties'] else content['type'])

# Extacting the info from template
def extractInfo(evaluatedTemplates, mainTemplateFilePath, createUiDefinitionFilePath):

    evaluatedTemplates.sort(key=sortContents)


    solutionPackage = {
        "Metadata": {},
        "DataConnectors": {
            "dataConnector": []
        },
        "AnalyticsRules": {
            "analyticsRule": []
        },
        "HuntingQueries": {
            "huntingQuery": []
        },
        "Workbooks": {
            "workbook": []
        },
        "Parsers": {
            "parser": []
        },
        "Playbooks": {
            "playbook": []
        },
        "LogicApps": {
            "logicAppsCustomConnector": []
        },
        "Watchlists": {
            "watchlist": []
        }
    }

    solutionPackage['Metadata'] = addMetadata(mainTemplateFilePath, createUiDefinitionFilePath)

    dataConnectorMapping = {}    

    for content in evaluatedTemplates:
        if content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'DataConnector':
            solutionPackage['DataConnectors']['dataConnector'].append(addDataConnector(content['properties'], dataConnectorMapping))
            solutionPackage['DataConnectors']['dataConnector'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'AnalyticsRule':
            solutionPackage['AnalyticsRules']['analyticsRule'].append(addAnalyticsRule(content['properties'], dataConnectorMapping))
            solutionPackage['AnalyticsRules']['analyticsRule'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'HuntingQuery':
            solutionPackage['HuntingQueries']['huntingQuery'].append(addHuntingQuery(content['properties']))
            solutionPackage['HuntingQueries']['huntingQuery'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'Workbook':
            solutionPackage['Workbooks']['workbook'].append(addWorkbook(content['properties']))
            solutionPackage['Workbooks']['workbook'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'Parser':
            solutionPackage['Parsers']['parser'].append(addParser(content['properties']))
            solutionPackage['Parsers']['parser'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'Playbook':
            solutionPackage['Playbooks']['playbook'].append(addPlaybook(content['properties']))
            solutionPackage['Playbooks']['playbook'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/contenttemplates'and content['properties']['contentKind'] == 'LogicApp':
            solutionPackage['LogicApps']['logicAppsCustomConnector'].append(addLogicAppsCustomConnector(content['properties']))
            solutionPackage['LogicApps']['logicAppsCustomConnector'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})
        elif content['type'] == 'Microsoft.SecurityInsights/Watchlists':
            solutionPackage['Watchlists']['watchlist'].append(addWatchlist(content['properties']))
            solutionPackage['Watchlists']['watchlist'][-1].update({"solutionSearchName": solutionPackage['Metadata']['searchKey']})

    return solutionPackage

# Write the files
def writeFiles(solutionPackage):
    with open(".\\templates\\solution.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage, file, indent=4)
        file.close()

    with open(".\\templates\\metadata.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['Metadata'], file, indent=4)
        file.close()

    with open(".\\templates\\dataConnectors.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['DataConnectors'], file, indent=4)
        file.close()

    with open(".\\templates\\analyticsRules.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['AnalyticsRules'], file, indent=4)
        file.close()

    with open(".\\templates\\huntingQueries.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['HuntingQueries'], file, indent=4)
        file.close()

    with open(".\\templates\\workbooks.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['Workbooks'], file, indent=4)
        file.close()

    with open(".\\templates\\parsers.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['Parsers'], file, indent=4)
        file.close()

    with open(".\\templates\\playbooks.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['Playbooks'], file, indent=4)
        file.close()

    with open(".\\templates\\logicApps.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['LogicApps'], file, indent=4)
        file.close()

    with open(".\\templates\\watchlists.json", 'w', encoding='utf-8') as file:
        json.dump(solutionPackage['Watchlists'], file, indent=4)
        file.close()
# Get Modified Files
def getModifiedFiles():
    gitRemoteCommand = "git remote"
    remoteResult = subprocess.run(gitRemoteCommand, shell=True, text=True, capture_output=True, check=True)
    
    if "origin" not in remoteResult.stdout.split():
        gitAddoriginCommand = f"git remote add origin {RepoUrl}"
        subprocess.run(gitAddoriginCommand, shell=True, text=True, capture_output=True, check=True)

    gitFetchOrigin = "git fetch origin master"
    
    subprocess.run(gitFetchOrigin, shell=True, text=True, capture_output=True, check=True)
    

    gitDiffCommand = "git diff origin/master --name-only"

    diffResult = subprocess.run(gitDiffCommand, shell=True, text=True, capture_output=True, check=True)
    
    modifiedFiles = [file for file in diffResult.stdout.split('\n') if re.match(r"Solutions/.*/Package/mainTemplate.json", file) or re.match(r"Solutions/.*/Package/createUiDefinition.json", file)]

    # for file in diffResult.stdout.split('\n'):
    #     if re.match(r"Solutions/.*/Package/mainTemplate.json", file) or re.match(r"Solutions/.*/Package/createUiDefinition.json", file):
    
    return modifiedFiles

# Main Function
def main():
    load_dotenv()

    modifiedFiles = getModifiedFiles()
    
    print(os.environ.get("SUBSCRIPTION_ID"))

    mainTemplateFilePath = ""
    createUiDefinitionFilePath = ""

    for file in modifiedFiles:
        if (file.endswith("mainTemplate.json")):
            mainTemplateFilePath = file
        elif (file.endswith("createUiDefinition.json")):
            createUiDefinitionFilePath = file

    
    # mainTemplateFilePath = "D:\\Solution Validation\\mainTemplate.json"
    # createUiDefinitionFilePath = "D:\\Solution Validation\\createUiDefinition.json"

    if mainTemplateFilePath == "":
        createUiDefinitionFilePath = mainTemplateFilePath.replace("mainTemplate.json", "createUiDefinition.json")
    if mainTemplateFilePath == "":
        mainTemplateFilePath = createUiDefinitionFilePath.replace( "createUiDefinition.json", "mainTemplate.json")
    
    print(mainTemplateFilePath, createUiDefinitionFilePath)
    
    with open(mainTemplateFilePath, 'r', encoding='utf-8') as file:
        mainTemplateFile = json.load(file)
        file.close()

    
    evaluatedTemplates = evaluateARMExpressions(mainTemplateFile)

    # with open("exportedTemplates.json", 'r', encoding='utf-8') as file:
    #     evaluatedTemplates = json.load(file)
    #     file.close()
        

    solutionPackage = extractInfo(evaluatedTemplates, mainTemplateFilePath, createUiDefinitionFilePath)

    print(solutionPackage)

    writeFiles(solutionPackage)
    


if __name__ == '__main__':
    main()
    print("Done")



