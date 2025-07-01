import os
from github import Github

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_EVENT_PATH = os.environ.get('GITHUB_EVENT_PATH')

# Load PR info
event = {}
if GITHUB_EVENT_PATH and os.path.exists(GITHUB_EVENT_PATH):
    with open(GITHUB_EVENT_PATH, 'r') as f:
        import json
        event = json.load(f)
pr_number = event.get('pull_request', {}).get('number')
repo_name = event.get('repository', {}).get('full_name')

# Parse errorformat: <file>:<line>:<col>: <message>
def parse_suggestions(file_path):
    suggestions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(':', 3)
            if len(parts) == 4:
                file, line_num, col, message = parts
                suggestions.append({
                    'file': file,
                    'line': int(line_num),
                    'col': int(col),
                    'message': message.strip()
                })
    return suggestions

def post_suggestion_comment(repo, pr, suggestion):
    body = f"**Grammar suggestion:**\n{suggestion['message']}"
    repo.create_pull_request_review_comment(
        body=body,
        pull_number=pr.number,
        commit_id=pr.head.sha,
        path=suggestion['file'],
        line=suggestion['line'],
        side='RIGHT'
    )

def main():
    if not (GITHUB_TOKEN and repo_name and pr_number):
        print("Missing GitHub context for commenting.")
        return
    if not os.path.exists('suggestions.txt'):
        print("No suggestions.txt file found.")
        return
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    suggestions = parse_suggestions('suggestions.txt')
    for suggestion in suggestions:
        try:
            post_suggestion_comment(repo, pr, suggestion)
        except Exception as e:
            print(f"Failed to post suggestion: {e}")

if __name__ == "__main__":
    main()
