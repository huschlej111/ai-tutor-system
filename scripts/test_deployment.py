#!/usr/bin/env python3
"""
Deployment Testing Script for Know-It-All Tutor System
Runs comprehensive tests against deployed infrastructure
"""
import argparse
import subprocess
import sys
import json
import os
import time
from typing import Dict, List, Any
from datetime import datetime


class DeploymentTester:
    """Comprehensive deployment testing"""
    
    def __init__(self, environment: str, region: str = "us-east-1"):
        self.environment = environment
        self.region = region
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all deployment tests"""
        print(f"🧪 Running comprehensive deployment tests for {self.environment}...")
        
        results = {
            "environment": self.environment,
            "test_time": datetime.utcnow().isoformat(),
            "test_suites": {}
        }
        
        # Test suites to run
        test_suites = [
            ("unit_tests", self._run_unit_tests),
            ("integration_tests", self._run_integration_tests),
            ("deployment_validation", self._run_deployment_validation),
            ("security_tests", self._run_security_tests),
            ("performance_tests", self._run_performance_tests),
            ("end_to_end_tests", self._run_end_to_end_tests)
        ]
        
        overall_success = True
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name.replace('_', ' ').title()}...")
            
            try:
                suite_result = test_function()
                results["test_suites"][suite_name] = suite_result
                
                if not suite_result.get("success", False):
                    overall_success = False
                    print(f"❌ {suite_name} failed")
                else:
                    print(f"✅ {suite_name} passed")
                    
            except Exception as e:
                results["test_suites"][suite_name] = {
                    "success": False,
                    "error": str(e),
                    "duration": 0
                }
                overall_success = False
                print(f"❌ {suite_name} failed with error: {str(e)}")
        
        results["overall_success"] = overall_success
        return results
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests"""
        start_time = time.time()
        
        try:
            # Run Python unit tests
            result = subprocess.run([
                "python", "-m", "pytest", "tests/", "-v",
                "--tb=short",
                "--junitxml=test-results/unit-tests.xml",
                "--cov=src",
                "--cov-report=xml:test-results/coverage.xml",
                "--cov-report=html:test-results/htmlcov",
                "-x"  # Stop on first failure for faster feedback
            ], capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Unit tests timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        start_time = time.time()
        
        try:
            # Run integration tests with LocalStack
            env = os.environ.copy()
            env.update({
                "ENVIRONMENT": "test",
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_DEFAULT_REGION": self.region,
                "LOCALSTACK_ENDPOINT": "http://localhost:4566"
            })
            
            result = subprocess.run([
                "python", "-m", "pytest", "tests/test_*integration*.py", "-v",
                "--tb=short",
                "--junitxml=test-results/integration-tests.xml"
            ], capture_output=True, text=True, env=env, timeout=600)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Integration tests timed out after 10 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _run_deployment_validation(self) -> Dict[str, Any]:
        """Run deployment validation tests"""
        start_time = time.time()
        
        try:
            # Run deployment validation
            env = os.environ.copy()
            env["ENVIRONMENT"] = self.environment
            
            result = subprocess.run([
                "python", "tests/test_deployment_validation.py",
                "--environment", self.environment,
                "--region", self.region,
                "--output-file", "test-results/deployment-validation.json"
            ], capture_output=True, text=True, env=env, timeout=900)
            
            success = result.returncode == 0
            
            # Try to load detailed results
            detailed_results = {}
            try:
                with open("test-results/deployment-validation.json", "r") as f:
                    detailed_results = json.load(f)
            except Exception:
                pass
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "detailed_results": detailed_results
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Deployment validation timed out after 15 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _run_security_tests(self) -> Dict[str, Any]:
        """Run security tests"""
        start_time = time.time()
        
        try:
            # Run security-focused tests
            result = subprocess.run([
                "python", "-m", "pytest", "tests/test_*security*.py", "-v",
                "--tb=short",
                "--junitxml=test-results/security-tests.xml"
            ], capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Security tests timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        start_time = time.time()
        
        try:
            # Run performance-focused tests
            env = os.environ.copy()
            env["ENVIRONMENT"] = self.environment
            
            result = subprocess.run([
                "python", "-m", "pytest", "tests/", "-v", "-k", "performance",
                "--tb=short",
                "--junitxml=test-results/performance-tests.xml"
            ], capture_output=True, text=True, env=env, timeout=600)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Performance tests timed out after 10 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def _run_end_to_end_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests"""
        start_time = time.time()
        
        try:
            # Run end-to-end workflow tests
            env = os.environ.copy()
            env["ENVIRONMENT"] = self.environment
            
            result = subprocess.run([
                "python", "-m", "pytest", "tests/", "-v", "-k", "e2e or end_to_end",
                "--tb=short",
                "--junitxml=test-results/e2e-tests.xml"
            ], capture_output=True, text=True, env=env, timeout=900)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "End-to-end tests timed out after 15 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def run_smoke_tests(self) -> Dict[str, Any]:
        """Run quick smoke tests for rapid feedback"""
        print(f"💨 Running smoke tests for {self.environment}...")
        
        start_time = time.time()
        
        try:
            # Run a subset of critical tests quickly
            result = subprocess.run([
                "python", "-m", "pytest", "tests/", "-v", "-k", "smoke or health",
                "--tb=short",
                "--maxfail=3",  # Stop after 3 failures
                "-x"  # Stop on first failure
            ], capture_output=True, text=True, timeout=120)
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "duration": time.time() - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": "Smoke tests timed out after 2 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    def generate_test_report(self, results: Dict[str, Any], output_file: str = None):
        """Generate a comprehensive test report"""
        
        # Create HTML report
        html_report = self._create_html_report(results)
        
        # Create JSON report
        json_report = json.dumps(results, indent=2, default=str)
        
        # Save reports
        if output_file:
            base_name = output_file.rsplit('.', 1)[0]
            
            # Save HTML report
            with open(f"{base_name}.html", "w") as f:
                f.write(html_report)
            
            # Save JSON report
            with open(f"{base_name}.json", "w") as f:
                f.write(json_report)
            
            print(f"📊 Test reports saved:")
            print(f"   HTML: {base_name}.html")
            print(f"   JSON: {base_name}.json")
        
        return html_report, json_report
    
    def _create_html_report(self, results: Dict[str, Any]) -> str:
        """Create HTML test report"""
        
        overall_status = "✅ PASSED" if results["overall_success"] else "❌ FAILED"
        status_color = "green" if results["overall_success"] else "red"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Deployment Test Report - {results['environment'].title()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .status {{ font-size: 24px; font-weight: bold; color: {status_color}; }}
        .suite {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .details {{ background: #f9f9f9; padding: 10px; margin: 10px 0; border-radius: 3px; }}
        .stdout {{ background: #f0f0f0; padding: 10px; font-family: monospace; white-space: pre-wrap; }}
        .stderr {{ background: #ffe6e6; padding: 10px; font-family: monospace; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Deployment Test Report</h1>
        <p><strong>Environment:</strong> {results['environment'].title()}</p>
        <p><strong>Test Time:</strong> {results['test_time']}</p>
        <p class="status">Overall Status: {overall_status}</p>
    </div>
"""
        
        # Add test suite results
        for suite_name, suite_result in results.get("test_suites", {}).items():
            suite_status = "✅ PASSED" if suite_result.get("success", False) else "❌ FAILED"
            suite_class = "success" if suite_result.get("success", False) else "failure"
            
            html += f"""
    <div class="suite">
        <div class="suite-header {suite_class}">
            {suite_name.replace('_', ' ').title()}: {suite_status}
        </div>
        <div class="details">
            <p><strong>Duration:</strong> {suite_result.get('duration', 0):.2f} seconds</p>
"""
            
            if suite_result.get("error"):
                html += f'<p><strong>Error:</strong> {suite_result["error"]}</p>'
            
            if suite_result.get("stdout"):
                html += f'<div class="stdout"><strong>Output:</strong><br>{suite_result["stdout"]}</div>'
            
            if suite_result.get("stderr"):
                html += f'<div class="stderr"><strong>Errors:</strong><br>{suite_result["stderr"]}</div>'
            
            html += """
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html


def main():
    """Main deployment testing script entry point"""
    parser = argparse.ArgumentParser(description="Test Know-It-All Tutor System deployment")
    parser.add_argument(
        "environment",
        choices=["development", "production"],
        help="Target environment to test"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run only smoke tests for quick feedback"
    )
    parser.add_argument(
        "--output-file",
        default="test-results/deployment-test-report",
        help="Output file for test report (without extension)"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating test report"
    )
    
    args = parser.parse_args()
    
    # Create test results directory
    os.makedirs("test-results", exist_ok=True)
    
    # Create deployment tester
    tester = DeploymentTester(
        environment=args.environment,
        region=args.region
    )
    
    # Run tests
    if args.smoke_only:
        results = {
            "environment": args.environment,
            "test_time": datetime.utcnow().isoformat(),
            "test_suites": {
                "smoke_tests": tester.run_smoke_tests()
            }
        }
        results["overall_success"] = results["test_suites"]["smoke_tests"]["success"]
    else:
        results = tester.run_all_tests()
    
    # Generate report
    if not args.no_report:
        tester.generate_test_report(results, args.output_file)
    
    # Print summary
    print(f"\n📊 Test Summary for {args.environment}:")
    print("=" * 50)
    
    for suite_name, suite_result in results["test_suites"].items():
        status = "✅ PASSED" if suite_result.get("success", False) else "❌ FAILED"
        duration = suite_result.get("duration", 0)
        print(f"{suite_name.replace('_', ' ').title()}: {status} ({duration:.2f}s)")
    
    print("=" * 50)
    
    if results["overall_success"]:
        print(f"🎉 All tests PASSED for {args.environment}!")
        sys.exit(0)
    else:
        print(f"💥 Some tests FAILED for {args.environment}!")
        sys.exit(1)


if __name__ == "__main__":
    main()