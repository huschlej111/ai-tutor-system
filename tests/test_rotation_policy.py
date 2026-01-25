#!/usr/bin/env python3
"""
Test script to verify key rotation policies are correctly configured.
Tests both LocalStack (2 days) and AWS production (6 months) configurations.
"""

import json
import os
import sys
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class RotationPolicyTester:
    """Test rotation policies for different environments."""
    
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url
        self.is_localstack = endpoint_url is not None
        
        # Configure clients
        if self.is_localstack:
            self.secrets_client = boto3.client(
                'secretsmanager',
                endpoint_url=endpoint_url,
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name="us-east-1"
            )
        else:
            self.secrets_client = boto3.client('secretsmanager')
    
    def test_rotation_configuration(self) -> Dict[str, Any]:
        """Test rotation configuration for all secrets."""
        results = {
            'environment': 'localstack' if self.is_localstack else 'aws',
            'expected_interval': 2 if self.is_localstack else 180,
            'secrets_tested': [],
            'errors': [],
            'summary': {}
        }
        
        # Test secrets that should have rotation configured
        test_secrets = [
            'tutor-system/database',
            'tutor-system/jwt'
        ]
        
        for secret_name in test_secrets:
            try:
                secret_result = self._test_secret_rotation(secret_name, results['expected_interval'])
                results['secrets_tested'].append(secret_result)
                
            except Exception as e:
                error_msg = f"Failed to test {secret_name}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _test_secret_rotation(self, secret_name: str, expected_interval: int) -> Dict[str, Any]:
        """Test rotation configuration for a specific secret."""
        result = {
            'secret_name': secret_name,
            'rotation_enabled': False,
            'rotation_interval': None,
            'matches_expected': False,
            'status': 'unknown'
        }
        
        try:
            # Get secret metadata
            response = self.secrets_client.describe_secret(SecretId=secret_name)
            
            result['rotation_enabled'] = response.get('RotationEnabled', False)
            
            if result['rotation_enabled']:
                rotation_rules = response.get('RotationRules', {})
                result['rotation_interval'] = rotation_rules.get('AutomaticallyAfterDays')
                result['matches_expected'] = result['rotation_interval'] == expected_interval
                
                if result['matches_expected']:
                    result['status'] = 'correct'
                    print(f"✅ {secret_name}: Rotation correctly configured ({result['rotation_interval']} days)")
                else:
                    result['status'] = 'incorrect_interval'
                    print(f"⚠️  {secret_name}: Rotation interval mismatch - expected {expected_interval}, got {result['rotation_interval']}")
            else:
                result['status'] = 'not_configured'
                print(f"❌ {secret_name}: Rotation not configured")
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                result['status'] = 'not_found'
                print(f"❌ {secret_name}: Secret not found")
            else:
                result['status'] = 'error'
                print(f"❌ {secret_name}: Error - {e.response['Error']['Message']}")
        
        return result
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary."""
        total_secrets = len(results['secrets_tested'])
        correct_configs = len([s for s in results['secrets_tested'] if s['status'] == 'correct'])
        
        return {
            'total_secrets_tested': total_secrets,
            'correctly_configured': correct_configs,
            'success_rate': f"{correct_configs}/{total_secrets}" if total_secrets > 0 else "0/0",
            'all_correct': correct_configs == total_secrets and total_secrets > 0,
            'recommendations': self._get_recommendations(results)
        }
    
    def _get_recommendations(self, results: Dict[str, Any]) -> list:
        """Get recommendations based on test results."""
        recommendations = []
        
        for secret in results['secrets_tested']:
            if secret['status'] == 'not_found':
                recommendations.append(f"Create secret: {secret['secret_name']}")
            elif secret['status'] == 'not_configured':
                recommendations.append(f"Configure rotation for: {secret['secret_name']}")
            elif secret['status'] == 'incorrect_interval':
                recommendations.append(
                    f"Update rotation interval for {secret['secret_name']} "
                    f"from {secret['rotation_interval']} to {results['expected_interval']} days"
                )
        
        if not recommendations:
            recommendations.append("All rotation policies are correctly configured!")
        
        return recommendations
    
    def configure_rotation_policy(self, secret_name: str, interval_days: int) -> bool:
        """Configure rotation policy for a secret."""
        try:
            # Note: This is a simplified example
            # In practice, you'd need to ensure the rotation Lambda exists
            lambda_arn = f"arn:aws:lambda:us-east-1:000000000000:function:tutor-secrets-rotation"
            
            self.secrets_client.rotate_secret(
                SecretId=secret_name,
                RotationLambdaArn=lambda_arn,
                RotationRules={
                    'AutomaticallyAfterDays': interval_days
                }
            )
            
            print(f"✅ Configured {interval_days}-day rotation for {secret_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure rotation for {secret_name}: {str(e)}")
            return False


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test rotation policy configuration")
    parser.add_argument("--localstack", action="store_true", 
                       help="Test LocalStack configuration")
    parser.add_argument("--endpoint", default="http://localhost:4566",
                       help="LocalStack endpoint URL")
    parser.add_argument("--configure", action="store_true",
                       help="Configure rotation policies if missing")
    parser.add_argument("--output", help="Output results to JSON file")
    
    args = parser.parse_args()
    
    # Initialize tester
    endpoint_url = args.endpoint if args.localstack else None
    tester = RotationPolicyTester(endpoint_url)
    
    print(f"🔄 Testing rotation policies...")
    print(f"Environment: {'LocalStack' if args.localstack else 'AWS'}")
    print(f"Expected interval: {2 if args.localstack else 180} days")
    print()
    
    # Run tests
    results = tester.test_rotation_configuration()
    
    # Configure missing policies if requested
    if args.configure:
        print("\n🔧 Configuring missing rotation policies...")
        expected_interval = results['expected_interval']
        
        for secret in results['secrets_tested']:
            if secret['status'] in ['not_configured', 'incorrect_interval']:
                tester.configure_rotation_policy(secret['secret_name'], expected_interval)
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"Total secrets tested: {results['summary']['total_secrets_tested']}")
    print(f"Correctly configured: {results['summary']['success_rate']}")
    print(f"All correct: {'✅ Yes' if results['summary']['all_correct'] else '❌ No'}")
    
    if results['summary']['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in results['summary']['recommendations']:
            print(f"  • {rec}")
    
    if results['errors']:
        print(f"\n❌ Errors:")
        for error in results['errors']:
            print(f"  • {error}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if results['summary']['all_correct'] else 1)


if __name__ == "__main__":
    main()