"""
IAM Policy Generator for Know-It-All Tutor System
Generates least privilege IAM policies for Lambda functions and services
"""

from typing import Dict, List, Any, Optional
import json


class IAMPolicyGenerator:
    """Generates least privilege IAM policies for the tutor system."""
    
    def __init__(self, environment: str, account_id: str, region: str):
        self.environment = environment
        self.account_id = account_id
        self.region = region
        self.resource_prefix = f"arn:aws:*:{region}:{account_id}"
    
    def generate_lambda_execution_policy(self, function_name: str) -> Dict[str, Any]:
        """Generate basic Lambda execution policy."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/lambda/{function_name}*"
                }
            ]
        }
    
    def generate_vpc_access_policy(self) -> Dict[str, Any]:
        """Generate VPC access policy for Lambda functions."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface"
                    ],
                    "Resource": "*"
                }
            ]
        }
    
    def generate_secrets_manager_policy(self, secret_names: List[str]) -> Dict[str, Any]:
        """Generate Secrets Manager access policy for specific secrets."""
        secret_arns = [
            f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:tutor-system/{self.environment}/{name}*"
            for name in secret_names
        ]

        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    "Resource": secret_arns
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt"
                    ],
                    "Resource": f"arn:aws:kms:{self.region}:{self.account_id}:key/*",
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com"
                        }
                    }
                }
            ]
        }
    
    def generate_rds_access_policy(self, cluster_identifier: str) -> Dict[str, Any]:
        """Generate RDS access policy for Aurora Serverless."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "rds-db:connect"
                    ],
                    "Resource": f"arn:aws:rds-db:{self.region}:{self.account_id}:dbuser:{cluster_identifier}/*"
                }
            ]
        }
    
    def generate_s3_access_policy(self, bucket_names: List[str], permissions: List[str] = None) -> Dict[str, Any]:
        """Generate S3 access policy for specific buckets."""
        if permissions is None:
            permissions = ["s3:GetObject", "s3:PutObject"]
        
        bucket_arns = [f"arn:aws:s3:::{bucket}" for bucket in bucket_names]
        object_arns = [f"arn:aws:s3:::{bucket}/*" for bucket in bucket_names]
        
        statements = []
        
        # Bucket-level permissions
        if any(perm.startswith("s3:List") or perm.startswith("s3:Get") for perm in permissions):
            statements.append({
                "Effect": "Allow",
                "Action": [perm for perm in permissions if not perm.endswith("Object")],
                "Resource": bucket_arns
            })
        
        # Object-level permissions
        object_permissions = [perm for perm in permissions if perm.endswith("Object")]
        if object_permissions:
            statements.append({
                "Effect": "Allow",
                "Action": object_permissions,
                "Resource": object_arns
            })
        
        return {
            "Version": "2012-10-17",
            "Statement": statements
        }
    
    def generate_cloudwatch_policy(self, metric_namespaces: List[str] = None) -> Dict[str, Any]:
        """Generate CloudWatch metrics policy."""
        if metric_namespaces is None:
            metric_namespaces = ["TutorSystem/*"]
        
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "cloudwatch:PutMetricData"
                    ],
                    "Resource": "*",
                    "Condition": {
                        "StringLike": {
                            "cloudwatch:namespace": metric_namespaces
                        }
                    }
                }
            ]
        }
    
    def generate_auth_function_policy(self) -> Dict[str, Any]:
        """Generate policy for authentication Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-auth"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials", "jwt-secret"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_cloudwatch_policy(["TutorSystem/Auth"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_domain_management_policy(self) -> Dict[str, Any]:
        """Generate policy for domain management Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-domain-management"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_cloudwatch_policy(["TutorSystem/Domain"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_quiz_engine_policy(self) -> Dict[str, Any]:
        """Generate policy for quiz engine Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-quiz-engine"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_cloudwatch_policy(["TutorSystem/Quiz"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_answer_evaluation_policy(self) -> Dict[str, Any]:
        """Generate policy for answer evaluation Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-answer-evaluation"),
            self.generate_vpc_access_policy(),
            self.generate_s3_access_policy([f"tutor-system-ml-models-{self.environment}"], ["s3:GetObject"]),
            self.generate_cloudwatch_policy(["TutorSystem/Evaluation"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_progress_tracking_policy(self) -> Dict[str, Any]:
        """Generate policy for progress tracking Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-progress-tracking"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_cloudwatch_policy(["TutorSystem/Progress"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_batch_upload_policy(self) -> Dict[str, Any]:
        """Generate policy for batch upload Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-batch-upload"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_s3_access_policy([f"tutor-system-uploads-{self.environment}"], ["s3:GetObject", "s3:PutObject"]),
            self.generate_cloudwatch_policy(["TutorSystem/BatchUpload"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_db_migration_policy(self) -> Dict[str, Any]:
        """Generate policy for database migration Lambda function."""
        policies = [
            self.generate_lambda_execution_policy("tutor-db-migration"),
            self.generate_vpc_access_policy(),
            self.generate_secrets_manager_policy(["database-credentials"]),
            self.generate_rds_access_policy(f"tutor-system-aurora-{self.environment}"),
            self.generate_cloudwatch_policy(["TutorSystem/Migration"])
        ]
        
        return self._merge_policies(policies)
    
    def generate_secrets_rotation_policy(self) -> Dict[str, Any]:
        """Generate policy for secrets rotation Lambda function."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/lambda/tutor-secrets-rotation*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:PutSecretValue",
                        "secretsmanager:UpdateSecretVersionStage",
                        "secretsmanager:UpdateSecret",
                        "secretsmanager:RotateSecret"
                    ],
                    "Resource": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:tutor-system/{self.environment}/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt",
                        "kms:GenerateDataKey",
                        "kms:DescribeKey"
                    ],
                    "Resource": f"arn:aws:kms:{self.region}:{self.account_id}:key/*",
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com"
                        }
                    }
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "rds:DescribeDBClusters",
                        "rds:DescribeDBInstances"
                    ],
                    "Resource": f"arn:aws:rds:{self.region}:{self.account_id}:cluster:tutor-system-aurora-{self.environment}"
                }
            ]
        }
    
    def generate_cloudtrail_policy(self) -> Dict[str, Any]:
        """Generate policy for CloudTrail service role."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/cloudtrail/tutor-system-{self.environment}*"
                }
            ]
        }
    
    def generate_config_service_policy(self) -> Dict[str, Any]:
        """Generate policy for AWS Config service role."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetBucketAcl",
                        "s3:ListBucket"
                    ],
                    "Resource": f"arn:aws:s3:::tutor-system-config-{self.environment}-{self.account_id}"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": f"arn:aws:s3:::tutor-system-config-{self.environment}-{self.account_id}/*"
                }
            ]
        }
    
    def _merge_policies(self, policies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple IAM policies into a single policy."""
        merged_statements = []
        
        for policy in policies:
            if "Statement" in policy:
                if isinstance(policy["Statement"], list):
                    merged_statements.extend(policy["Statement"])
                else:
                    merged_statements.append(policy["Statement"])
        
        return {
            "Version": "2012-10-17",
            "Statement": merged_statements
        }
    
    def export_policy_json(self, policy: Dict[str, Any], filename: str) -> None:
        """Export policy to JSON file."""
        with open(filename, 'w') as f:
            json.dump(policy, f, indent=2, default=str)


def generate_all_policies(environment: str, account_id: str, region: str = "us-east-1") -> Dict[str, Dict[str, Any]]:
    """Generate all IAM policies for the tutor system."""
    generator = IAMPolicyGenerator(environment, account_id, region)
    
    return {
        "auth_function": generator.generate_auth_function_policy(),
        "domain_management": generator.generate_domain_management_policy(),
        "quiz_engine": generator.generate_quiz_engine_policy(),
        "answer_evaluation": generator.generate_answer_evaluation_policy(),
        "progress_tracking": generator.generate_progress_tracking_policy(),
        "batch_upload": generator.generate_batch_upload_policy(),
        "db_migration": generator.generate_db_migration_policy(),
        "secrets_rotation": generator.generate_secrets_rotation_policy(),
        "cloudtrail_service": generator.generate_cloudtrail_policy(),
        "config_service": generator.generate_config_service_policy()
    }