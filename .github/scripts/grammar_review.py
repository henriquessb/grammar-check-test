import os
import requests
import json
import glob
from github import Github

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_EVENT_PATH = os.environ.get('GITHUB_EVENT_PATH')

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=" + GEMINI_API_KEY

# Load PR info
event = {}
if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
    with open(GITHUB_EVENT_PATH, 'r') as f:
        event = json.load(f)
pr_number = event.get('pull_request', {}).get('number')
repo_name = event.get('repository', {}).get('full_name')

# Find changed markdown files
def get_changed_md_files():
    files = []
    if 'pull_request' in event:
        files_url = event['pull_request']['url'] + '/files'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        resp = requests.get(files_url, headers=headers)
        for file in resp.json():
            if file['filename'].endswith('.md'):
                files.append(file['filename'])
    return files

def review_grammar(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    prompt = f"Review the following Markdown for grammar issues. Suggest corrections and explain any problems found. Do not show the whole original text. Only list the issues, where they occurred and the corrections, plus a summary of the review.\n\n{content}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(GEMINI_API_URL, headers=headers, json=data)
    if response.ok:
        result = response.json()
        try:
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            return "No review returned."
    else:
        return f"Error: {response.text}"

def post_pr_comment(body):
    if not (GITHUB_TOKEN and repo_name and pr_number):
        print("Missing GitHub context for commenting.")
        return
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment(body)

def main():
    files = get_changed_md_files()
    if not files:
        print("No Markdown files changed.")
        return
    for file in files:
        if os.path.exists(file):
            review = review_grammar(file)
            body = f"### Review for `{file}`\n{review}"
            post_pr_comment(body)

if __name__ == "__main__":
    main()
