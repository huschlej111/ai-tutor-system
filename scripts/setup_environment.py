#!/usr/bin/env python3
"""
Environment setup script for Know-It-All Tutor System
Creates virtual environment and installs dependencies
"""
import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run shell command and handle errors"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def create_virtual_environment():
    """Create Python virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return venv_path
    
    print("Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    return venv_path


def get_pip_command(venv_path):
    """Get pip command for the virtual environment"""
    if os.name == 'nt':  # Windows
        return str(venv_path / "Scripts" / "pip")
    else:  # Unix/Linux/macOS
        return str(venv_path / "bin" / "pip")


def get_python_command(venv_path):
    """Get python command for the virtual environment"""
    if os.name == 'nt':  # Windows
        return str(venv_path / "Scripts" / "python")
    else:  # Unix/Linux/macOS
        return str(venv_path / "bin" / "python")


def install_dependencies(venv_path):
    """Install project dependencies"""
    pip_cmd = get_pip_command(venv_path)
    
    # Upgrade pip
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install main dependencies
    print("Installing main dependencies...")
    run_command(f"{pip_cmd} install -r requirements.txt")
    
    # Install Lambda function dependencies
    print("Installing Lambda function dependencies...")
    run_command(f"{pip_cmd} install -r src/lambda_functions/requirements.txt")
    
    # Install CDK dependencies
    print("Installing CDK dependencies...")
    run_command(f"{pip_cmd} install -r infrastructure/requirements.txt")
    
    # Install project in development mode
    print("Installing project in development mode...")
    run_command(f"{pip_cmd} install -e .")


def setup_environment_file():
    """Set up environment configuration file"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("Please update .env file with your configuration values")
    else:
        print(".env file already exists or template not found")


def verify_aws_cli():
    """Verify AWS CLI is installed and configured"""
    try:
        result = run_command("aws --version", check=False)
        if result.returncode == 0:
            print("AWS CLI is installed")
            
            # Check if AWS is configured
            result = run_command("aws sts get-caller-identity", check=False)
            if result.returncode == 0:
                print("AWS CLI is configured")
            else:
                print("WARNING: AWS CLI is not configured. Run 'aws configure' to set up credentials")
        else:
            print("WARNING: AWS CLI is not installed. Please install it for deployment")
    except Exception as e:
        print(f"Could not verify AWS CLI: {e}")


def verify_node_npm():
    """Verify Node.js and npm are installed (required for CDK)"""
    try:
        result = run_command("node --version", check=False)
        if result.returncode == 0:
            print("Node.js is installed")
        else:
            print("WARNING: Node.js is not installed. Please install it for CDK deployment")
        
        result = run_command("npm --version", check=False)
        if result.returncode == 0:
            print("npm is installed")
        else:
            print("WARNING: npm is not installed. Please install it for CDK deployment")
    except Exception as e:
        print(f"Could not verify Node.js/npm: {e}")


def install_cdk():
    """Install AWS CDK CLI"""
    try:
        result = run_command("cdk --version", check=False)
        if result.returncode == 0:
            print("AWS CDK is already installed")
        else:
            print("Installing AWS CDK...")
            run_command("npm install -g aws-cdk")
    except Exception as e:
        print(f"Could not install CDK: {e}")


def main():
    """Main setup function"""
    print("Setting up Know-It-All Tutor System development environment...")
    
    # Verify prerequisites
    verify_aws_cli()
    verify_node_npm()
    
    # Create virtual environment
    venv_path = create_virtual_environment()
    
    # Install dependencies
    install_dependencies(venv_path)
    
    # Set up environment file
    setup_environment_file()
    
    # Install CDK
    install_cdk()
    
    print("\n" + "="*60)
    print("Setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. Update .env file with your configuration")
    print("3. Configure AWS CLI if not already done: aws configure")
    print("4. Bootstrap CDK: cdk bootstrap")
    print("5. Deploy infrastructure: cdk deploy")
    print("\nFor development:")
    print("- Run tests: pytest")
    print("- Format code: black src/")
    print("- Lint code: flake8 src/")


if __name__ == "__main__":
    main()