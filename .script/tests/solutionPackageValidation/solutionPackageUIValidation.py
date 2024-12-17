from dotenv import load_dotenv
import requests
import os
import re
import subprocess

RepoUrl = "https://github.com/Tintintani/Solution-Validation"
def main():
    modifiedFiles = getModifiedFiles()
    print(modifiedFiles)

def getModifiedFiles():
    gitRemoteCommand = "git remote"
    remoteResult = subprocess.run(gitRemoteCommand, shell=True, text = True, capture_output=True, check=True)
    
    if "origin" not in remoteResult.stdout.split():
        gitAddoriginCommand = f"git remote add origin {RepoUrl}"
        subprocess.run(gitAddoriginCommand, shell=True, text = True, capture_output=True, check=True)

    gitFetchOrigin = "git fetch origin master"
    
    subprocess.run(gitFetchOrigin, shell=True, text = True, capture_output=True, check=True)
    

    gitDiffCommand = f"git diff origin/master --name-only"

    diffResult = subprocess.run(gitDiffCommand, shell=True, text = True, capture_output=True, check=True)
    
    modifiedFiles = [file for file in diffResult.stdout.split('\n') if re.match(r"Solutions/.*/Package/mainTemplate.json", file) or re.match(r"Solutions/.*/Package/createUiDefinition.json", file)]

    # for file in diffResult.stdout.split('\n'):
    #     if re.match(r"Solutions/.*/Package/mainTemplate.json", file) or re.match(r"Solutions/.*/Package/createUiDefinition.json", file):
    
    return modifiedFiles

if __name__ == "__main__":
    load_dotenv()
    main()


