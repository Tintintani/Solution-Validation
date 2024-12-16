import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


baseUrl = "https://api.testim.io"

with open(".\\templates\\solution.json", 'r', encoding='utf-8') as file:
    solution = json.load(file)
    file.close()




