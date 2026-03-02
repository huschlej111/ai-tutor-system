"""
Network Stack for Know-It-All Tutor System
Contains VPC, security groups, and VPC endpoints
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput
)
from constructs import Construct


class NetworkStack(Stack):
    """
    Network infrastructure stack containing VPC and networking resources.
    This stack rarely changes and provides foundation for other stacks.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create VPC (Free Tier Optimized - 2 AZs for RDS requirement)
        self.vpc = ec2.Vpc(
            self,
            "TutorVPC",
            max_azs=2,  # Need 2 AZs for RDS subnet group requirement
            nat_gateways=0,  # No NAT Gateway ($32/month cost)
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,  # No NAT needed
                    cidr_mask=24
                )
            ]
        )
        
        # RDS Security Group - allows PostgreSQL access from Lambda
        self.rds_security_group = ec2.SecurityGroup(
            self,
            "RDSSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS PostgreSQL",
            allow_all_outbound=False
        )
        
        # Lambda Security Group
        self.lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True
        )
        
        # Allow Lambda to connect to RDS on PostgreSQL port
        self.rds_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to access RDS PostgreSQL"
        )
        
        # VPC Endpoint for S3 (Gateway endpoint - free)
        self.s3_endpoint = ec2.GatewayVpcEndpoint(
            self,
            "S3Endpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
        
        # CloudFormation Outputs
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name=f"{construct_id}-VpcId"
        )
        
        CfnOutput(
            self,
            "PublicSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
            description="Public Subnet IDs",
            export_name=f"{construct_id}-PublicSubnetIds"
        )
        
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
            description="Private Subnet IDs",
            export_name=f"{construct_id}-PrivateSubnetIds"
        )
        
        CfnOutput(
            self,
            "RdsSecurityGroupId",
            value=self.rds_security_group.security_group_id,
            description="RDS Security Group ID",
            export_name=f"{construct_id}-RdsSecurityGroupId"
        )
        
        CfnOutput(
            self,
            "LambdaSecurityGroupId",
            value=self.lambda_security_group.security_group_id,
            description="Lambda Security Group ID",
            export_name=f"{construct_id}-LambdaSecurityGroupId"
        )
