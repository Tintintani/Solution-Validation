import json
import re
import subprocess

result = subprocess.run('az account get-access-token --query accessToken --output json', capture_output=True, shell=True)
result = json.loads(result.stdout)
print(result)