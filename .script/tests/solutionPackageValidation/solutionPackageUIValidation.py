from dotenv import load_dotenv
import requests
import os
import subprocess

RepoUrl = "https://github.com/Tintintani/Solution-Validation"
def main():
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    modifiedFiles = getModifiedFiles(currentDirectory)
    print(modifiedFiles)

def getModifiedFiles(currentDirectory):
    gitRemoteCommand = "git remote"
    remoteResult = subprocess.run(gitRemoteCommand, shell=True, text = True, capture_output=True, check=True)
    print(remoteResult.stdout)
    
    if "origin" not in remoteResult.stdout.split():
        gitAddoriginCommand = f"git remote add origin {RepoUrl}"
        subprocess.run(gitAddoriginCommand, shell=True, check=True)

    gitFetchOrigin = "git fetch origin"
    
    try:
        subprocess.check_output(gitFetchOrigin, shell=True, text = True, capture_output=True, check=True).decode().split("\n")
    except subprocess.CalledProcessError as e:
        print(e)

    gitDiffCommand = f"git diff origin/master {currentDirectory} --name-only"

    diffResult = subprocess.run(gitDiffCommand, shell=True, text = True, capture_output=True, check=True)
    print(diffResult.stdout)

    return "f"

if __name__ == "__main__":
    load_dotenv()
    main()


