import os
from github import Github
import traceback

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
            parts = line.strip().split(':',3)
            if len(parts) == 4:
                file, line_num, col, message = parts
                suggestions.append({
                    'file': file,
                    'line': int(line_num),
                    'col': int(col),
                    'message': message
                })

    return suggestions

def post_suggestion_comment(pr, suggestion):
    commits = list(pr.get_commits())

    if not commits:
        print("No commits found in PR.")
        return

    body = suggestion['message'].replace('\\n', '\n')
    try:
        pr.create_review_comment(
            body=body,
            commit=commits[-1],
            path=suggestion['file'],
            line=int(suggestion['line'])
        )
    except Exception as e:
        print(f"Inline comment failed, posting as PR comment instead: {e}")
        pr.create_issue_comment(f"**Grammar suggestion for `{suggestion['file']}` line {suggestion['line']}**:\n{body}")

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
    print(f"Found {len(suggestions)} suggestions to post:")
    for suggestion in suggestions:
        try:
            post_suggestion_comment(pr, suggestion)
        except Exception as e:
            print(f"Failed to post suggestion: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
