import json
import sys
from pathlib import Path

ISSUE_FILE = "issues.json"
RDJSON_FILE = "suggestions.rdjson"

def load_issues(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def make_rdjson_diagnostic(filename, issue, original_lines):
    # RDFormat expects 1-based line and column numbers
    line_idx = issue["line"] - 1
    if line_idx < 0 or line_idx >= len(original_lines):
        # fallback to column 1 if out of range
        start_col = 1
        end_col = 1
    else:
        line = original_lines[line_idx]
        # Find the first occurrence of the text to be replaced
        text = issue["text"]
        if text in line:
            start_col = line.find(text) + 1
        else:
            print(f"[warn] Text '{text}' not found in line {issue['line']} of '{filename}'.")
            return {}
        end_col = start_col + len(text) if start_col > 0 else 1
    return {
        "message": issue["explanation"],
        "location": {
            "path": f"/{filename}",
            "range": {
                "start": {"line": issue["line"], "column": start_col},
                "end": {"line": issue["line"], "column": end_col}
            }
        },
        "suggestions": [
            {
                "range": {
                    "start": {"line": issue["line"], "column": start_col},
                    "end": {"line": issue["line"], "column": end_col}
                },
                "text": issue["correction"]
            }
        ],
        "severity": "INFO",
    }

def main():
    issues_data = load_issues(ISSUE_FILE)
    diagnostics = []
    for filename, issues in issues_data.items():
        if not Path(filename).is_file():
            print(f"[skip] File '{filename}' not found.")
            continue
        original_lines = Path(filename).read_text(encoding="utf-8").splitlines()
        for issue in issues:
            diagnostics.append(make_rdjson_diagnostic(filename, issue, original_lines))
        diagnostics = [d for d in diagnostics if d]
    rdjson = {
        "source": {"name": "AI Grammar Reviewer"},
        "diagnostics": diagnostics
    }

    print(rdjson)

    with open(RDJSON_FILE, "w", encoding="utf-8") as f:
        json.dump(rdjson, f, indent=2)
    print(f"[done] RDFormat suggestions written to {RDJSON_FILE}")

if __name__ == "__main__":
    main()
