from dotenv import load_dotenv
import requests
import os
import subprocess

RepoUrl = "https://github.com/Tintintani/Solution-Validation"
def main():
    modifiedFiles = getModifiedFiles()

def getModifiedFiles():
    gitRemoteCommand = "git remote"
    remoteResult = subprocess.run(gitRemoteCommand, shell=True, text = True, capture_output=True, check=True)
    
    if "origin" not in remoteResult.stdout.split():
        gitAddoriginCommand = f"git remote add origin {RepoUrl}"
        subprocess.run(gitAddoriginCommand, shell=True, check=True)

    gitFetchOrigin = "git fetch origin master"
    
    subprocess.run(gitFetchOrigin, shell=True, check=True)
    

    gitDiffCommand = f"git diff origin/master --name-only"

    diffResult = subprocess.run(gitDiffCommand, shell=True, text = True, capture_output=True, check=True)
    print(diffResult.stdout)

    return ""

if __name__ == "__main__":
    load_dotenv()
    main()


