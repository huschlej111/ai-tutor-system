#!/usr/bin/env python3
"""
Project setup validation script
Validates the project structure without requiring external dependencies
"""
import os
import sys
from pathlib import Path


def check_project_structure():
    """Check that all required directories exist"""
    print("🔍 Checking project structure...")
    
    required_dirs = [
        "src/lambda_functions",
        "src/shared",
        "infrastructure",
        "infrastructure/stacks",
        "scripts",
        "tests"
    ]
    
    all_good = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            all_good = False
    
    return all_good


def check_lambda_functions():
    """Check that all Lambda function handlers exist"""
    print("\n🔍 Checking Lambda functions...")
    
    lambda_functions = [
        "auth",
        "domain_management", 
        "quiz_engine",
        "answer_evaluation",
        "progress_tracking",
        "batch_upload",
        "db_migration"
    ]
    
    all_good = True
    for func in lambda_functions:
        func_path = Path(f"src/lambda_functions/{func}")
        handler_path = func_path / "handler.py"
        
        if func_path.exists() and handler_path.exists():
            print(f"  ✓ {func}")
        else:
            print(f"  ✗ {func} - MISSING")
            all_good = False
    
    return all_good


def check_shared_modules():
    """Check that shared utility modules exist"""
    print("\n🔍 Checking shared modules...")
    
    shared_modules = [
        "database.py",
        "auth_utils.py", 
        "config.py",
        "response_utils.py"
    ]
    
    all_good = True
    for module in shared_modules:
        module_path = Path(f"src/shared/{module}")
        if module_path.exists():
            print(f"  ✓ {module}")
        else:
            print(f"  ✗ {module} - MISSING")
            all_good = False
    
    return all_good


def check_infrastructure():
    """Check that CDK infrastructure files exist"""
    print("\n🔍 Checking infrastructure files...")
    
    infra_files = [
        "infrastructure/app.py",
        "infrastructure/stacks/tutor_system_stack.py",
        "cdk.json",
        "cdk.context.json"
    ]
    
    all_good = True
    for file_path in infra_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            all_good = False
    
    return all_good


def check_configuration():
    """Check that configuration files exist"""
    print("\n🔍 Checking configuration files...")
    
    config_files = [
        "requirements.txt",
        "src/lambda_functions/requirements.txt", 
        "infrastructure/requirements.txt",
        ".env.example",
        "setup.py",
        "pyproject.toml",
        "pytest.ini",
        ".gitignore",
        "Makefile"
    ]
    
    all_good = True
    for file_path in config_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            all_good = False
    
    return all_good


def check_scripts():
    """Check that deployment and setup scripts exist"""
    print("\n🔍 Checking scripts...")
    
    scripts = [
        "scripts/setup_environment.py",
        "scripts/deploy.py"
    ]
    
    all_good = True
    for script in scripts:
        if Path(script).exists():
            print(f"  ✓ {script}")
        else:
            print(f"  ✗ {script} - MISSING")
            all_good = False
    
    return all_good


def check_syntax():
    """Basic syntax check for Python files"""
    print("\n🔍 Checking Python syntax...")
    
    python_files = [
        "src/shared/database.py",
        "src/shared/config.py", 
        "src/shared/auth_utils.py",
        "src/shared/response_utils.py",
        "infrastructure/app.py",
        "infrastructure/stacks/tutor_system_stack.py",
        "scripts/setup_environment.py",
        "scripts/deploy.py"
    ]
    
    all_good = True
    for file_path in python_files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                print(f"  ✓ {file_path}")
            except SyntaxError as e:
                print(f"  ✗ {file_path} - SYNTAX ERROR: {e}")
                all_good = False
        else:
            print(f"  ✗ {file_path} - FILE NOT FOUND")
            all_good = False
    
    return all_good


def main():
    """Main validation function"""
    print("🚀 Know-It-All Tutor System - Project Setup Validation")
    print("=" * 60)
    
    checks = [
        check_project_structure,
        check_lambda_functions,
        check_shared_modules,
        check_infrastructure,
        check_configuration,
        check_scripts,
        check_syntax
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All validation checks passed!")
        print("\nNext steps:")
        print("1. Run: python scripts/setup_environment.py")
        print("2. Activate virtual environment")
        print("3. Configure .env file")
        print("4. Deploy infrastructure: make deploy")
    else:
        print("❌ Some validation checks failed!")
        print("Please fix the issues above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()