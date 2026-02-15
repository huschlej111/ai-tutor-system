#!/usr/bin/env python3
"""
Simple CDK App - Auth Only Stack
"""
import aws_cdk as cdk
from stacks.auth_only_stack import TutorSystemStack
from stacks.simple_monitoring_stack import SimpleMonitoringStack

app = cdk.App()

# Your AWS account and region
env_config = cdk.Environment(
    account="257949588978",
    region="us-east-1"
)

# Get optional notification email and budget from context
notification_email = app.node.try_get_context("notification_email")
monthly_budget = app.node.try_get_context("monthly_budget") or 10.0

# Create the main stack
auth_stack = TutorSystemStack(
    app,
    "TutorSystemStack-dev",
    env=env_config,
    description="Tutor System - Dev"
)

# Create the monitoring stack with cost tracking
monitoring_stack = SimpleMonitoringStack(
    app,
    "MonitoringStack-dev",
    env_name="dev",
    notification_email=notification_email,
    monthly_budget_limit=monthly_budget,
    env=env_config,
    description="Monitoring, Alerting, and Cost Tracking for Tutor System - Dev"
)

# Monitoring depends on main stack
monitoring_stack.add_dependency(auth_stack)

app.synth()
