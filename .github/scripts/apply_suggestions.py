import os
import requests
import json
import sys
import difflib

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")  # e.g. "owner/repo"
PR_NUMBER = os.getenv("PR_NUMBER")     # e.g. "42"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Parse diff manually (simplified, handles basic single-file hunks)
def parse_diff(file_path):
    suggestions = []
    with open(file_path, "r") as f:
        lines = f.readlines()

    current_file = None
    new_line_num = 0
    hunk_lines = []
    hunk_start = 0

    for line in lines:
        if line.startswith("+++ "):
            current_file = line.strip().split("+++ b/")[-1]
        elif line.startswith("@@"):
            # End previous suggestion if exists
            if hunk_lines:
                suggestion = {
                    "path": current_file,
                    "position": hunk_start,
                    "body": f"Suggested change\n```suggestion\n{''.join(hunk_lines).strip()}\n```"
                }
                suggestions.append(suggestion)
                hunk_lines = []

            hunk_meta = line.strip().split(" ")
            new_hunk_info = hunk_meta[2]
            hunk_start = int(new_hunk_info.split(",")[0][1:])  # e.g. +5 -> 5
            new_line_num = hunk_start
        elif line.startswith("+") and not line.startswith("+++"):
            hunk_lines.append(line[1:])
        elif line.startswith(" "):
            new_line_num += 1

    # Final hunk
    if hunk_lines:
        suggestion = {
            "path": current_file,
            "position": hunk_start,
            "body": f"Suggested change\n```suggestion\n{''.join(hunk_lines).strip()}\n```"
        }
        suggestions.append(suggestion)

    return suggestions

def post_review(suggestions):
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/reviews"

    data = {
        "body": "💡 Automated suggestions based on diff.",
        "event": "COMMENT",
        "comments": suggestions
    }

    r = requests.post(url, headers=HEADERS, json=data)
    if r.status_code >= 400:
        print(f"❌ Failed to post review: {r.status_code} - {r.text}")
    else:
        print(f"✅ Suggestions posted successfully!")

def main():
    if not GITHUB_TOKEN or not REPO or not PR_NUMBER:
        print("❌ Missing GITHUB_TOKEN, REPO, or PR_NUMBER in environment.")
        sys.exit(1)

    suggestions = parse_diff("suggestions.diff")

    if not suggestions:
        print("ℹ️ No suggestions found in diff.")
        return

    post_review(suggestions)

if __name__ == "__main__":
    main()