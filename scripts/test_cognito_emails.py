#!/usr/bin/env python3
"""
Test script for Cognito email functionality with MailHog
Tests user registration, email verification, and password reset flows
"""

import json
import time
import requests
import boto3
from typing import Dict, List, Optional
from botocore.exceptions import ClientError


class MailHogClient:
    """Client for interacting with MailHog API"""
    
    def __init__(self, base_url: str = "http://localhost:8025"):
        self.base_url = base_url
    
    def get_messages(self) -> List[Dict]:
        """Get all messages from MailHog"""
        response = requests.get(f"{self.base_url}/api/v2/messages")
        response.raise_for_status()
        return response.json().get('items', [])
    
    def get_latest_message(self, to_email: str) -> Optional[Dict]:
        """Get the latest message sent to a specific email address"""
        messages = self.get_messages()
        for message in messages:
            if any(to_email in recipient.get('Mailbox', '') for recipient in message.get('To', [])):
                return message
        return None
    
    def clear_messages(self):
        """Clear all messages from MailHog"""
        response = requests.delete(f"{self.base_url}/api/v1/messages")
        response.raise_for_status()
    
    def extract_verification_code(self, message: Dict) -> Optional[str]:
        """Extract verification code from Cognito email"""
        body = message.get('Content', {}).get('Body', '')
        
        # Look for common Cognito verification code patterns
        import re
        patterns = [
            r'verification code is:?\s*(\d{6})',
            r'code:?\s*(\d{6})',
            r'(\d{6})',  # Fallback: any 6-digit number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


class CognitoEmailTester:
    """Test Cognito email functionality"""
    
    def __init__(self):
        self.cognito_client = boto3.client(
            'cognito-idp',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            region_name='us-east-1'
        )
        self.mailhog = MailHogClient()
        self.user_pool_id = None
        self.client_id = None
    
    def setup_user_pool(self) -> Dict[str, str]:
        """Create a test user pool with email configuration"""
        try:
            # Create user pool
            user_pool_response = self.cognito_client.create_user_pool(
                PoolName='test-email-pool',
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': True
                    }
                },
                AutoVerifiedAttributes=['email'],
                AliasAttributes=['email'],
                EmailConfiguration={
                    'EmailSendingAccount': 'DEVELOPER',
                    'SourceArn': 'arn:aws:ses:us-east-1:000000000000:identity/noreply@test.com',
                    'ReplyToEmailAddress': 'noreply@test.com'
                },
                VerificationMessageTemplate={
                    'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                    'EmailMessage': 'Your verification code is: {####}',
                    'EmailSubject': 'Know-It-All Tutor - Verify your email'
                }
            )
            
            self.user_pool_id = user_pool_response['UserPool']['Id']
            
            # Create user pool client
            client_response = self.cognito_client.create_user_pool_client(
                UserPoolId=self.user_pool_id,
                ClientName='test-email-client',
                GenerateSecret=False,
                ExplicitAuthFlows=[
                    'ALLOW_USER_SRP_AUTH',
                    'ALLOW_REFRESH_TOKEN_AUTH',
                    'ALLOW_USER_PASSWORD_AUTH'
                ]
            )
            
            self.client_id = client_response['UserPoolClient']['ClientId']
            
            return {
                'user_pool_id': self.user_pool_id,
                'client_id': self.client_id
            }
            
        except ClientError as e:
            print(f"Error setting up user pool: {e}")
            raise
    
    def test_registration_email(self, email: str = "test@example.com") -> bool:
        """Test user registration and email verification flow"""
        print(f"\n🧪 Testing registration email flow for {email}")
        
        try:
            # Clear existing emails
            self.mailhog.clear_messages()
            
            # Register user
            print("📝 Registering user...")
            self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'false'}
                ],
                TemporaryPassword='TempPass123!',
                MessageAction='SUPPRESS'  # We'll trigger verification manually
            )
            
            # Trigger verification email
            print("📧 Triggering verification email...")
            self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': 'TempPass123!'
                }
            )
            
            # Wait for email delivery
            print("⏳ Waiting for email delivery...")
            time.sleep(2)
            
            # Check MailHog for email
            message = self.mailhog.get_latest_message(email)
            if not message:
                print("❌ No verification email received")
                return False
            
            print("✅ Verification email received!")
            print(f"   Subject: {message.get('Content', {}).get('Headers', {}).get('Subject', [''])[0]}")
            
            # Extract verification code
            verification_code = self.mailhog.extract_verification_code(message)
            if verification_code:
                print(f"🔑 Extracted verification code: {verification_code}")
                return True
            else:
                print("❌ Could not extract verification code from email")
                return False
                
        except ClientError as e:
            print(f"❌ Error during registration test: {e}")
            return False
    
    def test_password_reset_email(self, email: str = "test@example.com") -> bool:
        """Test forgot password email flow"""
        print(f"\n🧪 Testing password reset email flow for {email}")
        
        try:
            # Clear existing emails
            self.mailhog.clear_messages()
            
            # Trigger forgot password
            print("🔐 Triggering forgot password...")
            self.cognito_client.forgot_password(
                ClientId=self.client_id,
                Username=email
            )
            
            # Wait for email delivery
            print("⏳ Waiting for email delivery...")
            time.sleep(2)
            
            # Check MailHog for email
            message = self.mailhog.get_latest_message(email)
            if not message:
                print("❌ No password reset email received")
                return False
            
            print("✅ Password reset email received!")
            print(f"   Subject: {message.get('Content', {}).get('Headers', {}).get('Subject', [''])[0]}")
            
            # Extract reset code
            reset_code = self.mailhog.extract_verification_code(message)
            if reset_code:
                print(f"🔑 Extracted reset code: {reset_code}")
                return True
            else:
                print("❌ Could not extract reset code from email")
                return False
                
        except ClientError as e:
            print(f"❌ Error during password reset test: {e}")
            return False
    
    def test_email_templates(self) -> bool:
        """Test custom email templates"""
        print("\n🧪 Testing custom email templates")
        
        try:
            # Update user pool with custom templates
            self.cognito_client.update_user_pool(
                UserPoolId=self.user_pool_id,
                VerificationMessageTemplate={
                    'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                    'EmailMessage': '''
                    <h2>Welcome to Know-It-All Tutor!</h2>
                    <p>Thank you for registering. Your verification code is:</p>
                    <h3 style="color: #2563EB; font-family: monospace;">{####}</h3>
                    <p>Enter this code to verify your email address.</p>
                    ''',
                    'EmailSubject': '🎓 Welcome to Know-It-All Tutor - Verify Your Email'
                }
            )
            
            print("✅ Custom email templates configured")
            return True
            
        except ClientError as e:
            print(f"❌ Error configuring email templates: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            if self.user_pool_id:
                self.cognito_client.delete_user_pool(UserPoolId=self.user_pool_id)
                print("🧹 Cleaned up test user pool")
        except ClientError:
            pass  # Ignore cleanup errors


def main():
    """Run all email tests"""
    print("🚀 Starting Cognito Email Testing with MailHog")
    print("=" * 50)
    
    # Check MailHog availability
    try:
        requests.get("http://localhost:8025/api/v2/messages", timeout=5)
        print("✅ MailHog is running at http://localhost:8025")
    except requests.exceptions.RequestException:
        print("❌ MailHog is not running. Please start LocalStack with MailHog:")
        print("   make local-dev")
        return False
    
    tester = CognitoEmailTester()
    
    try:
        # Setup test environment
        print("\n🔧 Setting up test user pool...")
        pool_info = tester.setup_user_pool()
        print(f"✅ Created user pool: {pool_info['user_pool_id']}")
        
        # Run tests
        results = []
        
        # Test registration email
        results.append(tester.test_registration_email())
        
        # Test password reset email
        results.append(tester.test_password_reset_email())
        
        # Test custom templates
        results.append(tester.test_email_templates())
        
        # Print results
        print("\n" + "=" * 50)
        print("📊 Test Results:")
        print(f"   Registration Email: {'✅ PASS' if results[0] else '❌ FAIL'}")
        print(f"   Password Reset Email: {'✅ PASS' if results[1] else '❌ FAIL'}")
        print(f"   Custom Templates: {'✅ PASS' if results[2] else '❌ FAIL'}")
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        
        if all(results):
            print("🎉 All email tests passed!")
            print("🌐 View emails at: http://localhost:8025")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return all(results)
        
    finally:
        # Cleanup
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)