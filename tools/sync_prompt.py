import os
import re

def sync_prompt():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    prompt_file = os.path.join(repo_root, "prompt_template.txt")
    readme_file = os.path.join(repo_root, "README.md")

    if not os.path.exists(prompt_file):
        print(f"Error: {prompt_file} not found.")
        return

    with open(prompt_file, "r") as f:
        prompt_content = f.read().strip()

    if not os.path.exists(readme_file):
        print(f"Error: {readme_file} not found.")
        return

    with open(readme_file, "r") as f:
        readme_content = f.read()

    # Regex to find the Prompt section and the FIRST markdown code block that follows it
    pattern = re.compile(r"(## Prompt(?: Template)?\n(?:[\s\S]*?))(```markdown\n)([\s\S]*?)\n(```)", re.MULTILINE)
    
    if not pattern.search(readme_content):
        print("Error: Could not find '## Prompt' section with markdown code block in README.md")
        return

    new_readme_content = pattern.sub(rf"\1\2{prompt_content}\n\4", readme_content)

    if new_readme_content != readme_content:
        with open(readme_file, "w") as f:
            f.write(new_readme_content)
        print("Successfully updated README.md with the latest prompt template.")
    else:
        print("README.md is already up to date.")

if __name__ == "__main__":
    sync_prompt()
