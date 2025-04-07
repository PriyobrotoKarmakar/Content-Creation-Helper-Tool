import os
import subprocess
import sys
import time
import logging
from datetime import datetime

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Set up logging
logging.basicConfig(
    filename=f'git_operations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_command(command):
    """Run a shell command and return the output with enhanced terminal display."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}$ {command}{Colors.ENDC}")
    logging.info(f"Running command: {command}")
    
    try:
        # Show a spinner while command is running for long operations
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Simple spinner animation
        spinner = ['|', '/', '-', '\\']
        i = 0
        while process.poll() is None:
            sys.stdout.write(f"\r{Colors.CYAN}Processing {spinner[i % len(spinner)]}{Colors.ENDC}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        
        stdout, stderr = process.communicate()
        
        # Clear the spinner line
        sys.stdout.write('\r' + ' ' * 20 + '\r')
        sys.stdout.flush()
        
        if process.returncode == 0:
            if stdout:
                print(f"{Colors.GREEN}✓ Output:{Colors.ENDC}")
                # Print each line with a slight indent
                for line in stdout.strip().split('\n'):
                    print(f"  {line}")
                logging.info(f"Command output: {stdout.strip()}")
            print(f"{Colors.GREEN}✓ Command completed successfully{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}✗ Command failed with code {process.returncode}{Colors.ENDC}")
            if stderr:
                print(f"{Colors.FAIL}Error message:{Colors.ENDC}")
                for line in stderr.strip().split('\n'):
                    print(f"  {line}")
                logging.error(f"Command error: {stderr.strip()}")
            return False
    except Exception as e:
        print(f"{Colors.FAIL}✗ Exception occurred: {e}{Colors.ENDC}")
        logging.error(f"Exception: {e}")
        return False

def check_git_exists():
    """Check if git is installed."""
    return run_command("git --version")

def init_repo():
    """Initialize git repository if not already initialized."""
    if not os.path.exists(".git"):
        return run_command("git init")
    return True

def add_remote(remote_url):
    """Add a remote repository."""
    # Check if origin already exists
    result = subprocess.run("git remote -v", shell=True, text=True, stdout=subprocess.PIPE)
    if "origin" not in result.stdout:
        return run_command(f"git remote add origin {remote_url}")
    else:
        print(f"{Colors.WARNING}Remote 'origin' already exists.{Colors.ENDC}")
        return True

def stage_files():
    """Stage all files except those in .gitignore."""
    return run_command("git add .")

def commit(message):
    """Commit the staged changes."""
    return run_command(f'git commit -m "{message}"')

def push(branch="main"):
    """Push to remote repository."""
    return run_command(f"git push -u origin {branch}")

def set_name_email():
    """Set git user name and email if not already set."""
    try:
        # Check if name and email are already set
        name = subprocess.run("git config --global user.name", shell=True, text=True, 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        email = subprocess.run("git config --global user.email", shell=True, text=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if not name.stdout.strip():
            name_input = input(f"{Colors.CYAN}Enter your Git username: {Colors.ENDC}")
            run_command(f'git config --global user.name "{name_input}"')
        
        if not email.stdout.strip():
            email_input = input(f"{Colors.CYAN}Enter your Git email: {Colors.ENDC}")
            run_command(f'git config --global user.email "{email_input}"')
            
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Error setting name and email: {e}{Colors.ENDC}")
        logging.error(f"Error setting name and email: {e}")
        return False

def check_branch_name():
    """Check current branch name and rename to main if necessary."""
    result = subprocess.run("git branch --show-current", shell=True, text=True, stdout=subprocess.PIPE)
    current_branch = result.stdout.strip()
    
    if current_branch == "master":
        response = input(f"{Colors.WARNING}Your branch is named 'master'. Do you want to rename it to 'main'? (y/n): {Colors.ENDC}")
        if response.lower() == 'y':
            return run_command("git branch -M main")
    elif not current_branch:
        print(f"{Colors.WARNING}No branches exist yet. First commit will create the main branch.{Colors.ENDC}")
    return True

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}Git Repository Setup Assistant{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*50}{Colors.ENDC}")
    
    if not check_git_exists():
        print(f"{Colors.FAIL}Git is not installed or not in PATH. Please install Git first.{Colors.ENDC}")
        return
    
    print(f"\n{Colors.BOLD}Step 1: Repository Initialization{Colors.ENDC}")
    init_repo()
    
    print(f"\n{Colors.BOLD}Step 2: Setting Git Identity{Colors.ENDC}")
    set_name_email()
    
    print(f"\n{Colors.BOLD}Step 3: Remote Repository Configuration{Colors.ENDC}")
    remote_url = input(f"{Colors.CYAN}Enter your GitHub repository URL (leave blank if already configured): {Colors.ENDC}")
    if remote_url:
        add_remote(remote_url)
    
    print(f"\n{Colors.BOLD}Step 4: Branch Configuration{Colors.ENDC}")
    check_branch_name()
    
    print(f"\n{Colors.BOLD}Step 5: Staging Files{Colors.ENDC}")
    stage_files()
    
    print(f"\n{Colors.BOLD}Step 6: Committing Changes{Colors.ENDC}")
    commit_msg = input(f"{Colors.CYAN}Enter commit message (leave blank to use existing): {Colors.ENDC}")
    if commit_msg:
        commit(commit_msg)
    
    print(f"\n{Colors.BOLD}Step 7: Pushing to Remote Repository{Colors.ENDC}")
    branch_name = subprocess.run("git branch --show-current", shell=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    if not branch_name:
        branch_name = "main"
        print(f"{Colors.CYAN}No branch detected. Using 'main' as default.{Colors.ENDC}")
    else:
        print(f"{Colors.CYAN}Current branch: {branch_name}{Colors.ENDC}")
    
    push_result = push(branch_name)
    
    print(f"\n{Colors.HEADER}{'='*50}{Colors.ENDC}")
    if push_result:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Successfully pushed to repository!{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}❌ Failed to push to repository.{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Troubleshooting tips:{Colors.ENDC}")
        print(f"{Colors.CYAN}1. Make sure you have the correct permissions for the repository{Colors.ENDC}")
        print(f"{Colors.CYAN}2. Check if the remote repository URL is correct with 'git remote -v'{Colors.ENDC}")
        print(f"{Colors.CYAN}3. Try authenticating with a personal access token instead of password{Colors.ENDC}")
        print(f"{Colors.CYAN}4. Ensure you have committed changes before pushing{Colors.ENDC}")
        print(f"{Colors.CYAN}5. Pull remote changes first with 'git pull origin {branch_name}' if needed{Colors.ENDC}")
        
        # Add option to see the git status
        print(f"\n{Colors.BOLD}Would you like to see the current git status?{Colors.ENDC}")
        if input(f"{Colors.CYAN}Enter y/n: {Colors.ENDC}").lower() == 'y':
            run_command("git status")
            
        # Add option to try pull first
        print(f"\n{Colors.BOLD}Would you like to try pulling from remote first?{Colors.ENDC}")
        if input(f"{Colors.CYAN}Enter y/n: {Colors.ENDC}").lower() == 'y':
            run_command(f"git pull origin {branch_name}")
            
            print(f"\n{Colors.BOLD}Try pushing again?{Colors.ENDC}")
            if input(f"{Colors.CYAN}Enter y/n: {Colors.ENDC}").lower() == 'y':
                push(branch_name)
    
    print(f"\n{Colors.CYAN}A log file has been created with details of this session.{Colors.ENDC}")

if __name__ == "__main__":
    main()
