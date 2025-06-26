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
    original_lines = Path(filename).read_text(encoding="utf-8").splitlines()
    modified_lines = original_lines[:]

    # Track which lines have suggestions and their explanations
    suggestions = {}

    for issue in issues:
        line_idx = issue["line"] - 1  # 0-based index
        if line_idx < 0 or line_idx >= len(modified_lines):
            print(f"[warn] Line {issue['line']} for text '{issue['text']}' is out of range in {filename}")
            continue
        original_line = modified_lines[line_idx]
        if issue["text"] not in original_line:
            print(f"[warn] Text '{issue['text']}' not found in line {issue['line']} of {filename}")
            continue
        modified_lines[line_idx] = original_line.replace(issue["text"], issue["correction"], 1)
        suggestions[line_idx] = issue["explanation"]

    diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"/{filename}",
            tofile=f"/{filename}",
            lineterm=""
        )
    )

    # Insert explanation comments after each suggestion hunk
    if suggestions:
        new_diff = []
        i = 0
        while i < len(diff):
            new_diff.append(diff[i])
            # Look for suggestion lines (those starting with '+', but not '+++')
            if diff[i].startswith('@@'):
                # Find the line numbers in the hunk header
                hunk_header = diff[i]
                # Parse the hunk header to get the starting line number in the new file
                import re
                m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", hunk_header)
                if m:
                    start_line = int(m.group(1)) - 1
                    line_offset = 0
                    i += 1
                    while i < len(diff) and not diff[i].startswith('@@'):
                        if diff[i].startswith('+') and not diff[i].startswith('+++'):
                            line_no = start_line + line_offset
                            if line_no in suggestions:
                                # Insert the comment line after this suggestion
                                new_diff.append(f"# comment: {suggestions[line_no]}")
                        if not diff[i].startswith('-'):
                            line_offset += 1
                        new_diff.append(diff[i])
                        i += 1
                    continue
            i += 1
        diff = new_diff

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
        with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(all_diffs) + "\n")
        print(f"[done] Suggestions written to {SUGGESTIONS_FILE}")
        print("\n".join(all_diffs) + "\n")
    else:
        print("[done] No diffs generated.")


if __name__ == "__main__":
    main()
