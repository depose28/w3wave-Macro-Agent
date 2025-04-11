import os
import requests
import base64
from pathlib import Path

# GitHub API configuration
GITHUB_TOKEN = "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"
GITHUB_USERNAME = "depose28"
REPO_NAME = "macro-agent"

# API endpoints
BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def create_repository():
    """Create a new GitHub repository."""
    url = f"{BASE_URL}/user/repos"
    data = {
        "name": REPO_NAME,
        "description": "A Supabase Edge Function that generates daily macro market insights from Twitter data",
        "private": True,
        "auto_init": False
    }
    response = requests.post(url, headers=HEADERS, json=data)
    response.raise_for_status()
    return response.json()

def get_file_content(file_path):
    """Get the content of a file and encode it in base64."""
    with open(file_path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')

def create_file(path, content):
    """Create a file in the GitHub repository."""
    url = f"{BASE_URL}/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{path}"
    data = {
        "message": f"Add {path}",
        "content": content
    }
    response = requests.put(url, headers=HEADERS, json=data)
    response.raise_for_status()
    return response.json()

def main():
    try:
        # Create repository
        print("Creating repository...")
        repo = create_repository()
        print(f"Repository created: {repo['html_url']}")

        # Files to upload
        files_to_upload = [
            "supabase/functions/macro-agent/index.py",
            "supabase/functions/macro-agent/requirements.txt",
            "supabase/functions/macro-agent/Dockerfile",
            "supabase/migrations/20240411000000_setup_scheduler.sql",
            ".gitignore",
            "README.md"
        ]

        # Upload files
        for file_path in files_to_upload:
            if os.path.exists(file_path):
                print(f"Uploading {file_path}...")
                content = get_file_content(file_path)
                create_file(file_path, content)
                print(f"Uploaded {file_path}")

        print("\nRepository setup complete!")
        print(f"Repository URL: {repo['html_url']}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 