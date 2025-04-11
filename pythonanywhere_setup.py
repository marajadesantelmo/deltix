"""
PythonAnywhere Setup Script for Deltix

This script helps set up the necessary files and configurations for 
running Deltix on PythonAnywhere with Twilio WhatsApp integration.

Run this script after uploading your files to PythonAnywhere.
"""

import os
import sys
import subprocess
import requests

def check_requirements():
    """Check if required packages are installed, if not install them"""
    required_packages = [
        'flask',
        'twilio',
        'requests',
        'openai',
        'supabase',
        'pandas'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} installed successfully")

def create_wsgi_file():
    """Create or update the WSGI file for PythonAnywhere"""
    wsgi_path = f"/home/facundol/mysite/wsgi.py"
    wsgi_content = f"""import sys
import os

# Add your project directory to the Python path
project_home = f'/home/facundol/deltix'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import your Flask application
from webhook import app as application
"""
    
    try:
        with open(wsgi_path, 'w') as f:
            f.write(wsgi_content)
        print(f"✅ WSGI file created at {wsgi_path}")
    except Exception as e:
        print(f"❌ Failed to create WSGI file: {str(e)}")
        print("You'll need to manually create the WSGI file with this content:")
        print(wsgi_content)

def check_github_access():
    """Check if the GitHub repository is accessible"""
    try:
        response = requests.get("https://raw.githubusercontent.com/marajadesantelmo/deltix/main/README.md")
        if response.status_code == 200:
            print("✅ GitHub repository is accessible")
        else:
            print(f"⚠️ GitHub repository returned status code {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to access GitHub repository: {str(e)}")

def main():
    print("🤖 Setting up Deltix on PythonAnywhere...")
    
    # Check requirements
    print("\n📋 Checking required packages...")
    check_requirements()
    
    # Check GitHub access
    print("\n🔍 Checking GitHub repository access...")
    check_github_access()
    
    # Create WSGI file
    print("\n📝 Setting up WSGI file...")
    create_wsgi_file()
    
    print("\n🎉 Setup complete! Next steps:")
    print("1. Make sure your 'webhook.py' file is accessible")
    print("2. Configure a Twilio WhatsApp Sandbox or Business account")
    print("3. Set up your webhook URL in Twilio (https://yourusername.pythonanywhere.com/webhook)")
    print("4. Reload your PythonAnywhere web app")
    print("5. Test your WhatsApp integration by sending a message to your Twilio number")

if __name__ == "__main__":
    main()
