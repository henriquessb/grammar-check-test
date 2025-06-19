import json
import os
import difflib
import shutil
from pathlib import Path
import tempfile

ISSUE_FILE = "issues.json"
SUGGESTIONS_FILE = "suggestions.diff"


def load_issues(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_issues_and_generate_diff(filename, issues):
    original_lines = Path(filename).read_text(encoding="utf-8").splitlines(keepends=True)
    modified_lines = original_lines[:]

    for issue in issues:
        line_idx = issue["line"] - 1  # 0-based index
        original_line = modified_lines[line_idx]
        if issue["text"] not in original_line:
            print(f"[warn] Text '{issue['text']}' not found in line {issue['line']} of {filename}")
            continue
        modified_line = original_line.replace(issue["text"], issue["correction"], 1)
        modified_lines[line_idx] = f"{modified_line.replace("\n", "")}  # Suggestion: {issue["explanation"]}"

    diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"/{filename}",
            tofile=f"/{filename}",
            lineterm=""
        )
    )

    return diff


def main():
    issues_data = load_issues(ISSUE_FILE)
    all_diffs = []
    print(issues_data)
    for filename, issues in issues_data.items():
        if not Path(filename).is_file():
            print(f"[skip] File '{filename}' not found.")
            continue
        diff = apply_issues_and_generate_diff(filename, issues)
        if diff:
            all_diffs.extend(diff)


    if all_diffs:
        # Remove empty elements from all_diffs
        all_diffs = [line for line in all_diffs if line.strip() != ""]
        all_diffs.append("")
        with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(all_diffs))
        print(f"[done] Suggestions written to {SUGGESTIONS_FILE}")
        print(all_diffs)
    else:
        print("[done] No diffs generated.")


if __name__ == "__main__":
    main()
