import json
from pathlib import Path

ISSUE_FILE = "issues.json"
EFM_FILE = "suggestions.txt"

# errorformat: %f:%l:%c: %m

def load_issues(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    issues_data = load_issues(ISSUE_FILE)
    lines = []
    for filename, issues in issues_data.items():
        if not Path(filename).is_file():
            print(f"[skip] File '{filename}' not found.")
            continue
        original_lines = Path(filename).read_text(encoding="utf-8").splitlines()
        for issue in issues:
            line_idx = issue["line"] - 1
            if line_idx < 0 or line_idx >= len(original_lines):
                col = 1
            else:
                line = original_lines[line_idx]
                text = issue["text"]
                if text in line:
                    col = line.find(text) + 1
                    modified_line = line.replace(issue["text"], issue["correction"], 1)
                    msg = f"{issue['explanation'].strip()}\\n```suggestion\\n{modified_line}\\n```"
                    lines.append(f"{filename}:{issue['line']}:{col}: {msg}")
                else:
                    print(f"[warn] Text '{text}' not found in line {issue['line']} of '{filename}'.")
                    continue
    with open(EFM_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[done] Errorformat suggestions written to {EFM_FILE}")

if __name__ == "__main__":
    main()
