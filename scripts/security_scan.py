#!/usr/bin/env python3
"""
Security scanning script for the Know-It-All Tutor system.
Runs all static security analysis tools and generates consolidated reports.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SecurityScanner:
    """Orchestrates security scanning tools for the project."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "security-reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_bandit(self, target_paths: List[str]) -> Tuple[bool, str]:
        """Run Bandit SAST scanning on Python code."""
        print("🔍 Running Bandit SAST scanning...")
        
        cmd = [
            "bandit",
            "-r",  # Recursive
            "-f", "json",  # JSON format
            "-o", str(self.reports_dir / "bandit-report.json"),
            "--severity-level", "medium",
            "--confidence-level", "medium",
        ] + target_paths
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            # Bandit returns non-zero exit code when issues are found
            if result.returncode == 0:
                print("✅ Bandit: No security issues found")
                return True, "No issues found"
            elif result.returncode == 1:
                print("⚠️  Bandit: Security issues found")
                return False, "Security issues detected"
            else:
                print(f"❌ Bandit: Error running scan: {result.stderr}")
                return False, f"Scan error: {result.stderr}"
                
        except FileNotFoundError:
            print("❌ Bandit not found. Install with: pip install bandit")
            return False, "Tool not installed"
        except Exception as e:
            print(f"❌ Bandit: Unexpected error: {e}")
            return False, f"Unexpected error: {e}"
    
    def run_checkov(self) -> Tuple[bool, str]:
        """Run Checkov infrastructure security validation."""
        print("🔍 Running Checkov infrastructure scanning...")
        
        cmd = [
            "checkov",
            "--config-file", ".checkov.yml",
            "--output", "json",
            "--output-file-path", str(self.reports_dir / "checkov-report.json"),
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Checkov: No infrastructure security issues found")
                return True, "No issues found"
            else:
                print("⚠️  Checkov: Infrastructure security issues found")
                return False, "Infrastructure security issues detected"
                
        except FileNotFoundError:
            print("❌ Checkov not found. Install with: pip install checkov")
            return False, "Tool not installed"
        except Exception as e:
            print(f"❌ Checkov: Unexpected error: {e}")
            return False, f"Unexpected error: {e}"
    
    def run_trufflehog(self) -> Tuple[bool, str]:
        """Run TruffleHog secrets detection."""
        print("🔍 Running TruffleHog secrets detection...")
        
        cmd = [
            "trufflehog",
            "filesystem",
            ".",
            "--config", ".truffleHogConfig.yml",
            "--json",
            "--no-update",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            # Save output to file
            output_file = self.reports_dir / "trufflehog-report.json"
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            # Check if secrets were found
            if result.stdout.strip():
                secrets_found = len(result.stdout.strip().split('\n'))
                print(f"⚠️  TruffleHog: {secrets_found} potential secrets found")
                return False, f"{secrets_found} potential secrets detected"
            else:
                print("✅ TruffleHog: No secrets found")
                return True, "No secrets found"
                
        except FileNotFoundError:
            print("❌ TruffleHog not found. Install from: https://github.com/trufflesecurity/trufflehog")
            return False, "Tool not installed"
        except Exception as e:
            print(f"❌ TruffleHog: Unexpected error: {e}")
            return False, f"Unexpected error: {e}"
    
    def run_pip_audit(self) -> Tuple[bool, str]:
        """Run pip-audit dependency vulnerability scanning."""
        print("🔍 Running pip-audit dependency scanning...")
        
        cmd = [
            "pip-audit",
            "--format", "json",
            "--output", str(self.reports_dir / "pip-audit-report.json"),
            "--desc",
            "--progress-spinner",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ pip-audit: No vulnerable dependencies found")
                return True, "No vulnerable dependencies"
            else:
                print("⚠️  pip-audit: Vulnerable dependencies found")
                return False, "Vulnerable dependencies detected"
                
        except FileNotFoundError:
            print("❌ pip-audit not found. Install with: pip install pip-audit")
            return False, "Tool not installed"
        except Exception as e:
            print(f"❌ pip-audit: Unexpected error: {e}")
            return False, f"Unexpected error: {e}"
    
    def generate_summary_report(self, results: Dict[str, Tuple[bool, str]]) -> None:
        """Generate a consolidated security summary report."""
        print("\n📊 Generating security summary report...")
        
        summary = {
            "scan_timestamp": datetime.now().isoformat(),
            "project": "Know-It-All Tutor System",
            "tools": {},
            "overall_status": "PASS",
            "issues_found": False,
            "recommendations": []
        }
        
        for tool, (success, message) in results.items():
            summary["tools"][tool] = {
                "status": "PASS" if success else "FAIL",
                "message": message,
                "report_file": f"{tool.replace('_', '-')}-report.json"
            }
            
            if not success:
                summary["overall_status"] = "FAIL"
                summary["issues_found"] = True
        
        # Add recommendations based on findings
        if summary["issues_found"]:
            summary["recommendations"] = [
                "Review individual tool reports for detailed findings",
                "Address high and critical severity issues first",
                "Update dependencies with known vulnerabilities",
                "Remove or secure any exposed secrets",
                "Review infrastructure configurations for security best practices"
            ]
        else:
            summary["recommendations"] = [
                "Continue regular security scanning",
                "Keep dependencies up to date",
                "Monitor for new security advisories"
            ]
        
        # Save summary report
        summary_file = self.reports_dir / "security-summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print(f"\n🎯 Security Scan Summary:")
        print(f"   Overall Status: {'❌ FAIL' if summary['issues_found'] else '✅ PASS'}")
        print(f"   Timestamp: {summary['scan_timestamp']}")
        print(f"   Report Location: {summary_file}")
        
        for tool, info in summary["tools"].items():
            status_icon = "❌" if info["status"] == "FAIL" else "✅"
            print(f"   {tool}: {status_icon} {info['message']}")
    
    def run_all_scans(self, target_paths: Optional[List[str]] = None) -> bool:
        """Run all security scanning tools."""
        if target_paths is None:
            target_paths = ["src/", "infrastructure/", "scripts/"]
        
        print("🚀 Starting comprehensive security scan...")
        print(f"📁 Target paths: {', '.join(target_paths)}")
        print(f"📊 Reports will be saved to: {self.reports_dir}")
        print("-" * 60)
        
        results = {}
        
        # Run each security tool
        results["bandit"] = self.run_bandit(target_paths)
        results["checkov"] = self.run_checkov()
        results["trufflehog"] = self.run_trufflehog()
        results["pip_audit"] = self.run_pip_audit()
        
        # Generate summary report
        self.generate_summary_report(results)
        
        # Return overall success status
        return all(success for success, _ in results.values())


def main():
    """Main entry point for the security scanner."""
    parser = argparse.ArgumentParser(
        description="Run security analysis tools for the Know-It-All Tutor system"
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["src/", "infrastructure/", "scripts/"],
        help="Paths to scan (default: src/ infrastructure/ scripts/)"
    )
    parser.add_argument(
        "--tool",
        choices=["bandit", "checkov", "trufflehog", "pip-audit", "all"],
        default="all",
        help="Specific tool to run (default: all)"
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with non-zero code if security issues are found"
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    scanner = SecurityScanner(project_root)
    
    # Run specified tool(s)
    if args.tool == "all":
        success = scanner.run_all_scans(args.paths)
    elif args.tool == "bandit":
        success, _ = scanner.run_bandit(args.paths)
    elif args.tool == "checkov":
        success, _ = scanner.run_checkov()
    elif args.tool == "trufflehog":
        success, _ = scanner.run_trufflehog()
    elif args.tool == "pip-audit":
        success, _ = scanner.run_pip_audit()
    
    # Exit with appropriate code
    if args.fail_on_issues and not success:
        print("\n❌ Security scan failed - issues found")
        sys.exit(1)
    else:
        print("\n✅ Security scan completed")
        sys.exit(0)


if __name__ == "__main__":
    main()