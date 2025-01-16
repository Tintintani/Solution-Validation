import requests
import os


accessToken = os.environ.get('GITHUB_TOKEN')
repo = "Tintintani/Solution-Validation"
prNumber = 10
url = f"https://api.github.com/repos/{repo}/issues/{prNumber}/comments"
headers = {
    'Authorization': f'Bearer {accessToken}',
    'Accept': 'application/json'
}
comment = "### UI Test - Testim Results\n\n"

executionResult = ["Test Passed", "Test Failed"]
for result in executionResult:
    comment += f"- {result}\n"
payload = {
    "body": comment
}
try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Error while Posting Comment")
    raise