import os
import json
import requests
from github import Github
from google import genai
import sys

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_EVENT_PATH = os.environ.get('GITHUB_EVENT_PATH')

# Load PR info
event = {}
if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
    with open(GITHUB_EVENT_PATH, 'r') as f:
        event = json.load(f)
pr_number = event.get('pull_request', {}).get('number')
repo_name = event.get('repository', {}).get('full_name')

# Find changed markdown files
def get_changed_md_files():
    valid_folders = ('docs/guides', 'docs/troubleshooting', 'docs/faststore', 'docs/release-notes')

    files = []
    if 'pull_request' in event:
        files_url = event['pull_request']['url'] + '/files'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        resp = requests.get(files_url, headers=headers)
        for file in resp.json():
            if file['filename'].endswith(('.md','.mdx')) and file['filename'].startswith(valid_folders):
                files.append(file['filename'])
    return files

def review_grammar(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    response_schema = {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "integer"},
                        "text": {"type": "string"},
                        "correction": {"type": "string"},
                        "explanation": {"type": "string"}
                    },
                    "required": ["line", "text", "correction", "explanation"]
                }
            },
            "summary": {"type": "string"}
        },
        "required": ["issues", "summary"]
    }

    prompt = (
        "Review the following Markdown for grammar issues. "
        "Return a JSON object with an 'issues' array (each with line, text, correction, explanation) and a 'summary' string. "
        "Do not show the whole original text. Only list the issues, where they occurred and the corrections, plus a summary of the review.\n\n"
        f"{content}"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.2,
            "response_schema": response_schema
        }
    )
    try:
        return response.text
    except Exception:
        return "No review returned."

def make_rdjson_diagnostic(file, issue):
    return {
        "message": issue["explanation"],
        "location": {
            "path": file,
            "range": {
                "start": {"line": issue["line"], "column": 1},
                "end": {"line": issue["line"], "column": 1}
            }
        },
        "suggestions": [
            {
                "range": {
                    "start": {"line": issue["line"], "column": 1},
                    "end": {"line": issue["line"], "column": 1}
                },
                "text": issue["correction"]
            }
        ],
        "severity": "INFO",
        "code": {"value": "AI Grammar"}
    }

def main():
    files = get_changed_md_files()
    if not files:
        print("No Markdown files changed.")
        return
    diagnostics = []
    summaries = []
    for file in files:
        if os.path.exists(file):
            review = review_grammar(file)
            try:
                review_json = json.loads(review)
            except Exception:
                continue
            for issue in review_json.get("issues", []):
                diagnostics.append(make_rdjson_diagnostic(file, issue))
            summaries.append(f"### Review for `{file}`\n{review_json.get('summary', '')}")
    # Write rdjson for reviewdog
    rdjson = {
        "source": {"name": "ai-grammar-review", "url": "https://github.com/reviewdog/reviewdog"},
        "diagnostics": diagnostics
    }
    with open("reviewdog_output.json", "w", encoding="utf-8") as f:
        json.dump(rdjson, f)
    # Write summaries for PR comment
    with open("grammar_summaries.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(summaries))

if __name__ == "__main__":
    main()
