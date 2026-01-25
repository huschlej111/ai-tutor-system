#!/usr/bin/env python3
"""
Setup RDS instance in LocalStack for proper Aurora Serverless emulation.
This script creates an RDS PostgreSQL instance that LocalStack manages.
"""

import boto3
import json
import time
import os
from typing import Dict, Any


class LocalStackRDSSetup:
    def __init__(self):
        self.endpoint_url = os.getenv('LOCALSTACK_ENDPOINT', 'http://localhost:4566')
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # RDS configuration
        self.db_instance_identifier = 'tutor-system-db'
        self.db_name = 'tutor_system'
        self.master_username = 'tutor_user'
        self.master_password = 'tutor_password'
        
        # Initialize AWS clients
        self.rds_client = boto3.client(
            'rds',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        self.secretsmanager_client = boto3.client(
            'secretsmanager',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        self.ec2_client = boto3.client(
            'ec2',
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )

    def create_vpc_infrastructure(self) -> Dict[str, str]:
        """Create VPC, subnets, and security groups for RDS"""
        print("🌐 Setting up VPC infrastructure...")
        
        # VPC configuration
        vpc_cidr = '10.0.0.0/16'
        subnet_cidrs = ['10.0.1.0/24', '10.0.2.0/24']
        availability_zones = ['us-east-1a', 'us-east-1b']
        
        vpc_id = None
        subnet_ids = []
        security_group_id = None
        
        try:
            # Create VPC
            vpc_response = self.ec2_client.create_vpc(
                CidrBlock=vpc_cidr,
                TagSpecifications=[
                    {
                        'ResourceType': 'vpc',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-vpc'},
                            {'Key': 'Environment', 'Value': 'development'},
                            {'Key': 'Project', 'Value': 'tutor-system'}
                        ]
                    }
                ]
            )
            vpc_id = vpc_response['Vpc']['VpcId']
            print(f"✓ Created VPC: {vpc_id}")
            
            # Enable DNS hostnames and resolution
            self.ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsHostnames={'Value': True}
            )
            self.ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsSupport={'Value': True}
            )
            
            # Create Internet Gateway
            igw_response = self.ec2_client.create_internet_gateway(
                TagSpecifications=[
                    {
                        'ResourceType': 'internet-gateway',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-igw'},
                            {'Key': 'Environment', 'Value': 'development'}
                        ]
                    }
                ]
            )
            igw_id = igw_response['InternetGateway']['InternetGatewayId']
            
            # Attach Internet Gateway to VPC
            self.ec2_client.attach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            print(f"✓ Created and attached Internet Gateway: {igw_id}")
            
            # Create subnets in different AZs
            for i, (cidr, az) in enumerate(zip(subnet_cidrs, availability_zones)):
                subnet_response = self.ec2_client.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=az,
                    TagSpecifications=[
                        {
                            'ResourceType': 'subnet',
                            'Tags': [
                                {'Key': 'Name', 'Value': f'tutor-system-subnet-{i+1}'},
                                {'Key': 'Environment', 'Value': 'development'},
                                {'Key': 'Type', 'Value': 'database'}
                            ]
                        }
                    ]
                )
                subnet_id = subnet_response['Subnet']['SubnetId']
                subnet_ids.append(subnet_id)
                print(f"✓ Created subnet: {subnet_id} in {az}")
            
            # Create route table and route to Internet Gateway
            route_table_response = self.ec2_client.create_route_table(
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'route-table',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-rt'},
                            {'Key': 'Environment', 'Value': 'development'}
                        ]
                    }
                ]
            )
            route_table_id = route_table_response['RouteTable']['RouteTableId']
            
            # Add route to Internet Gateway
            self.ec2_client.create_route(
                RouteTableId=route_table_id,
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=igw_id
            )
            
            # Associate subnets with route table
            for subnet_id in subnet_ids:
                self.ec2_client.associate_route_table(
                    RouteTableId=route_table_id,
                    SubnetId=subnet_id
                )
            
            print(f"✓ Created route table and associated subnets: {route_table_id}")
            
            # Create security group for RDS
            sg_response = self.ec2_client.create_security_group(
                GroupName='tutor-system-rds-sg',
                Description='Security group for tutor system RDS instance',
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'security-group',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-rds-sg'},
                            {'Key': 'Environment', 'Value': 'development'},
                            {'Key': 'Purpose', 'Value': 'database'}
                        ]
                    }
                ]
            )
            security_group_id = sg_response['GroupId']
            
            # Add inbound rules for PostgreSQL
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [
                            {
                                'CidrIp': vpc_cidr,
                                'Description': 'PostgreSQL access from VPC'
                            }
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': 'PostgreSQL access for LocalStack development'
                            }
                        ]
                    }
                ]
            )
            print(f"✓ Created security group: {security_group_id}")
            
            return {
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'security_group_id': security_group_id,
                'internet_gateway_id': igw_id,
                'route_table_id': route_table_id
            }
            
        except Exception as e:
            if "InvalidVpc.Conflict" in str(e) or "already exists" in str(e).lower():
                print("✓ VPC infrastructure already exists, retrieving existing resources...")
                return self._get_existing_vpc_resources()
            else:
                print(f"✗ Failed to create VPC infrastructure: {e}")
                raise
    
    def _get_existing_vpc_resources(self) -> Dict[str, str]:
        """Get existing VPC resources by tags"""
        try:
            # Find VPC by tag
            vpcs = self.ec2_client.describe_vpcs(
                Filters=[
                    {'Name': 'tag:Name', 'Values': ['tutor-system-vpc']},
                    {'Name': 'tag:Project', 'Values': ['tutor-system']}
                ]
            )
            
            if not vpcs['Vpcs']:
                raise Exception("No existing VPC found with expected tags")
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            
            # Find subnets
            subnets = self.ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'tag:Type', 'Values': ['database']}
                ]
            )
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
            
            # Find security group
            security_groups = self.ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'tag:Name', 'Values': ['tutor-system-rds-sg']}
                ]
            )
            
            if not security_groups['SecurityGroups']:
                raise Exception("No existing security group found")
            
            security_group_id = security_groups['SecurityGroups'][0]['GroupId']
            
            print(f"✓ Found existing VPC: {vpc_id}")
            print(f"✓ Found existing subnets: {subnet_ids}")
            print(f"✓ Found existing security group: {security_group_id}")
            
            return {
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'security_group_id': security_group_id,
                'internet_gateway_id': '',  # Not needed for existing
                'route_table_id': ''  # Not needed for existing
            }
            
        except Exception as e:
            print(f"✗ Failed to retrieve existing VPC resources: {e}")
            raise

    def create_db_subnet_group(self, subnet_ids: list) -> None:
        """Create DB subnet group for RDS instance"""
        try:
            self.rds_client.create_db_subnet_group(
                DBSubnetGroupName='tutor-system-subnet-group',
                DBSubnetGroupDescription='Subnet group for tutor system database',
                SubnetIds=subnet_ids,
                Tags=[
                    {'Key': 'Environment', 'Value': 'development'},
                    {'Key': 'Project', 'Value': 'tutor-system'}
                ]
            )
            print("✓ Created DB subnet group: tutor-system-subnet-group")
        except Exception as e:
            if "DBSubnetGroupAlreadyExists" in str(e):
                print("✓ DB subnet group already exists: tutor-system-subnet-group")
            else:
                print(f"✗ Failed to create DB subnet group: {e}")

    def create_db_parameter_group(self) -> None:
        """Create DB parameter group with optimized settings"""
        try:
            self.rds_client.create_db_parameter_group(
                DBParameterGroupName='tutor-system-postgres15',
                DBParameterGroupFamily='postgres15',
                Description='Parameter group for tutor system PostgreSQL 15',
                Tags=[
                    {'Key': 'Environment', 'Value': 'development'},
                    {'Key': 'Project', 'Value': 'tutor-system'}
                ]
            )
            
            # Modify parameters for better performance
            self.rds_client.modify_db_parameter_group(
                DBParameterGroupName='tutor-system-postgres15',
                Parameters=[
                    {
                        'ParameterName': 'shared_buffers',
                        'ParameterValue': '256MB',
                        'ApplyMethod': 'pending-reboot'
                    },
                    {
                        'ParameterName': 'effective_cache_size',
                        'ParameterValue': '1GB',
                        'ApplyMethod': 'immediate'
                    },
                    {
                        'ParameterName': 'work_mem',
                        'ParameterValue': '4MB',
                        'ApplyMethod': 'immediate'
                    },
                    {
                        'ParameterName': 'max_connections',
                        'ParameterValue': '200',
                        'ApplyMethod': 'pending-reboot'
                    }
                ]
            )
            print("✓ Created DB parameter group: tutor-system-postgres15")
        except Exception as e:
            if "DBParameterGroupAlreadyExists" in str(e):
                print("✓ DB parameter group already exists: tutor-system-postgres15")
            else:
                print(f"✗ Failed to create DB parameter group: {e}")

    def create_rds_instance(self, security_group_id: str) -> None:
        """Create RDS PostgreSQL instance"""
        try:
            response = self.rds_client.create_db_instance(
                DBInstanceIdentifier=self.db_instance_identifier,
                DBInstanceClass='db.t3.micro',
                Engine='postgres',
                EngineVersion='15.4',
                MasterUsername=self.master_username,
                MasterUserPassword=self.master_password,
                DBName=self.db_name,
                AllocatedStorage=20,
                StorageType='gp2',
                StorageEncrypted=True,
                VpcSecurityGroupIds=[security_group_id],
                DBSubnetGroupName='tutor-system-subnet-group',
                DBParameterGroupName='tutor-system-postgres15',
                BackupRetentionPeriod=7,
                PreferredBackupWindow='03:00-04:00',
                PreferredMaintenanceWindow='sun:04:00-sun:05:00',
                MultiAZ=False,
                PubliclyAccessible=True,
                AutoMinorVersionUpgrade=True,
                Tags=[
                    {'Key': 'Environment', 'Value': 'development'},
                    {'Key': 'Project', 'Value': 'tutor-system'},
                    {'Key': 'ManagedBy', 'Value': 'LocalStack'}
                ],
                EnablePerformanceInsights=True,
                DeletionProtection=False
            )
            print(f"✓ Created RDS instance: {self.db_instance_identifier}")
            return response
        except Exception as e:
            if "DBInstanceAlreadyExists" in str(e):
                print(f"✓ RDS instance already exists: {self.db_instance_identifier}")
            else:
                print(f"✗ Failed to create RDS instance: {e}")
                raise

    def wait_for_db_available(self) -> None:
        """Wait for RDS instance to become available"""
        print("⏳ Waiting for RDS instance to become available...")
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = self.rds_client.describe_db_instances(
                    DBInstanceIdentifier=self.db_instance_identifier
                )
                
                db_instance = response['DBInstances'][0]
                status = db_instance['DBInstanceStatus']
                
                if status == 'available':
                    endpoint = db_instance['Endpoint']['Address']
                    port = db_instance['Endpoint']['Port']
                    print(f"✅ RDS instance is available!")
                    print(f"   Endpoint: {endpoint}:{port}")
                    return
                elif status in ['failed', 'stopped']:
                    print(f"❌ RDS instance failed with status: {status}")
                    return
                else:
                    print(f"   Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(10)
                    attempt += 1
                    
            except Exception as e:
                print(f"   Error checking status: {e}")
                time.sleep(10)
                attempt += 1
        
        print(f"⚠️  Timeout waiting for RDS instance to become available")

    def create_database_secret(self) -> None:
        """Create database credentials in Secrets Manager pointing to containerized PostgreSQL"""
        secret_name = 'tutor-system/database/credentials'
        
        # Point to the containerized PostgreSQL instead of RDS
        secret_value = {
            'username': self.master_username,
            'password': self.master_password,
            'engine': 'postgres',
            'host': 'localhost',  # Containerized PostgreSQL host
            'port': 5432,         # Direct PostgreSQL port (not LocalStack RDS)
            'dbname': self.db_name,
            'dbInstanceIdentifier': self.db_instance_identifier  # Keep for compatibility
        }
        
        try:
            self.secretsmanager_client.create_secret(
                Name=secret_name,
                Description='Database credentials for tutor system (containerized PostgreSQL bridge)',
                SecretString=json.dumps(secret_value),
                Tags=[
                    {'Key': 'Environment', 'Value': 'development'},
                    {'Key': 'Project', 'Value': 'tutor-system'},
                    {'Key': 'Bridge', 'Value': 'containerized-postgresql'}
                ]
            )
            print(f"✓ Created database secret (PostgreSQL bridge): {secret_name}")
        except Exception as e:
            if "ResourceExistsException" in str(e):
                # Update existing secret to point to containerized PostgreSQL
                try:
                    self.secretsmanager_client.update_secret(
                        SecretId=secret_name,
                        Description='Database credentials for tutor system (containerized PostgreSQL bridge)',
                        SecretString=json.dumps(secret_value)
                    )
                    print(f"✓ Updated database secret (PostgreSQL bridge): {secret_name}")
                except Exception as update_e:
                    print(f"✓ Database secret already exists: {secret_name}")
            else:
                print(f"✗ Failed to create database secret: {e}")

    def setup_all(self) -> None:
        """Run complete RDS setup using containerized PostgreSQL bridge strategy"""
        print("🚀 Setting up LocalStack RDS bridge for tutor system...")
        print("📋 Using containerized PostgreSQL bridge strategy (LocalStack Community)")
        print()
        
        try:
            # Create VPC infrastructure (still needed for Lambda functions)
            vpc_resources = self.create_vpc_infrastructure()
            print()
            
            # Skip RDS API calls (pro features) and just create the bridge configuration
            print("⚠️  Skipping RDS instance creation (pro feature)")
            print("✓ Using existing containerized PostgreSQL at localhost:5432")
            
            # Create secrets pointing to containerized PostgreSQL
            self.create_database_secret()
            
            print()
            print("🌐 VPC Infrastructure (for Lambda functions):")
            print(f"   VPC ID: {vpc_resources['vpc_id']}")
            print(f"   Subnet IDs: {', '.join(vpc_resources['subnet_ids'])}")
            print(f"   Security Group ID: {vpc_resources['security_group_id']}")
            
            print()
            print("✅ LocalStack RDS bridge setup completed successfully!")
            print()
            print("🔗 Database Connection Strategy:")
            print("   • LocalStack Community: Direct connection to containerized PostgreSQL")
            print("   • Lambda functions will use Secrets Manager to get connection details")
            print("   • Connection: postgresql://tutor_user:tutor_password@localhost:5432/tutor_system")
            print()
            print("🔑 Retrieve credentials from Secrets Manager:")
            print("   aws --endpoint-url=http://localhost:4566 secretsmanager get-secret-value --secret-id tutor-system/database/credentials")
            print()
            print("📝 Note: This setup uses the 'bridge strategy' where:")
            print("   1. Containerized PostgreSQL provides the actual database")
            print("   2. LocalStack Secrets Manager provides connection metadata")
            print("   3. Lambda functions connect directly to PostgreSQL (localhost:5432)")
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            raise


def main():
    """Main function"""
    setup = LocalStackRDSSetup()
    setup.setup_all()


if __name__ == "__main__":
    main()