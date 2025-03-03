import os
import subprocess
import time

repo_directory = '/home/facundol/deltix'

# Function to check for changes in the directory
def check_changes():
    try:
        # Run git status to check for changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_directory,
            capture_output=True,
            text=True
        )
        # If the result is empty, no changes
        return len(result.stdout.strip()) > 0
    except Exception as e:
        print(f"Error checking for changes: {e}")
        return False

# Function to push changes to GitHub
def commit_and_push():
    try:
        # Stage all changes
        subprocess.run(['git', 'add', '.'], cwd=repo_directory)
        
        # Commit the changes
        current_time = time.strftime("%H:%M")
        commit_message = f"Update {current_time}"
        subprocess.run(['git', 'commit', '-m', commit_message], cwd=repo_directory)
        
        # Push to GitHub
        subprocess.run(['git', 'push'], cwd=repo_directory)
        print("Changes pushed to GitHub")
    except Exception as e:
        print(f"Error pushing changes: {e}")

# Run once to check and push changes
def main():
    if check_changes():
        print("Changes detected, pushing to GitHub...")
        commit_and_push()
    else:
        print("No changes detected.")


if __name__ == "__main__":
    main()
