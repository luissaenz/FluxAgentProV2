import re
from pathlib import Path

def count_tools(filepath):
    if not Path(filepath).exists():
        return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Count occurrences of "tool_id": 
    return len(re.findall(r'"tool_id":', content))

if __name__ == "__main__":
    for i in range(1, 5):
        path = f"docs/prompt{i}.txt"
        print(f"{path}: {count_tools(path)} tools")
