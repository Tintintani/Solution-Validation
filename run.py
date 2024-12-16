import os
from dotenv import load_dotenv

load_dotenv()

with open("changedFiles.txt", 'r') as f:
    file = f.read()
    f.close()
print(file)
