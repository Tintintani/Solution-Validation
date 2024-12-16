import requests
import json

apiKey = "tanishqarora12345"
url = f"https://https://tanishq-test-functionapp.azurewebsites.net//api/http_trigger1?code={apiKey}"

data = {
    "name": "Tanishq",
    "age": 20
}

response = requests.post(url, data=json.dumps(data))
print(response)