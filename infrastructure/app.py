#!/usr/bin/env python3
"""
AWS CDK App for Know-It-All Tutor System
"""
import aws_cdk as cdk
from constructs import Construct
from stacks.tutor_system_stack import TutorSystemStack
from stacks.security_monitoring_stack import SecurityMonitoringStack
from stacks.pipeline_stack import PipelineStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import MonitoringStack


app = cdk.App()

# Get environment configuration
environment = app.node.try_get_context("environment") or "development"
account = app.node.try_get_context("account")
region = app.node.try_get_context("region") or "us-east-1"

# Get domain configuration (optional)
domain_name = app.node.try_get_context("domain_name")
certificate_arn = app.node.try_get_context("certificate_arn")

# Get notification email for alerts (optional)
notification_email = app.node.try_get_context("notification_email")

# Create environment configuration
env_config = cdk.Environment(account=account, region=region)

# Create the CI/CD pipeline stack (deployed once per environment)
pipeline_stack = PipelineStack(
    app,
    f"PipelineStack-{environment}",
    environment=environment,
    env=env_config,
    description=f"CI/CD Pipeline for Know-It-All Tutor System - {environment} environment"
)

# Create the security monitoring stack
security_stack = SecurityMonitoringStack(
    app,
    f"SecurityMonitoringStack-{environment}",
    environment=environment,
    env=env_config,
    description=f"Security Monitoring for Know-It-All Tutor System - {environment} environment"
)

# Create the main application stack
main_stack = TutorSystemStack(
    app,
    f"TutorSystemStack-{environment}",
    environment=environment,
    env=env_config,
    description=f"Know-It-All Tutor System - {environment} environment"
)

# Create the frontend hosting stack
frontend_stack = FrontendStack(
    app,
    f"FrontendStack-{environment}",
    environment=environment,
    domain_name=domain_name,
    certificate_arn=certificate_arn,
    env=env_config,
    description=f"Frontend Hosting for Know-It-All Tutor System - {environment} environment"
)

# Create the monitoring and alerting stack
monitoring_stack = MonitoringStack(
    app,
    f"MonitoringStack-{environment}",
    environment=environment,
    notification_email=notification_email,
    env=env_config,
    description=f"Monitoring and Alerting for Know-It-All Tutor System - {environment} environment"
)

# Add dependencies to ensure proper deployment order
main_stack.add_dependency(security_stack)
main_stack.add_dependency(pipeline_stack)
frontend_stack.add_dependency(main_stack)
monitoring_stack.add_dependency(main_stack)
monitoring_stack.add_dependency(frontend_stack)

app.synth()