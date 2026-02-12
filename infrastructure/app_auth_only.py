#!/usr/bin/env python3
"""
Simple CDK App - Auth Only Stack
"""
import aws_cdk as cdk
from stacks.auth_only_stack import TutorSystemStack

app = cdk.App()

# Your AWS account and region
env_config = cdk.Environment(
    account="257949588978",  # Your account from earlier
    region="us-east-1"
)

# Create the stack with its FINAL name
auth_stack = TutorSystemStack(
    app,
    "TutorSystemStack-dev",  # Same name as your full stack will use
    env=env_config,
    description="Tutor System - Dev (Auth Only for now)"
)

app.synth()
