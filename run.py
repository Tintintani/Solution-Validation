import os
from dotenv import load_dotenv

load_dotenv()

fileName = os.environ.get('CHANGED_FILES')

with open(fileName, 'r') as f:
    file = f.read()
    f.close()
print(file)
