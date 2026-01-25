"""
Frontend Hosting Stack for Know-It-All Tutor System
Implements S3 + CloudFront distribution for React application
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deployment,
    aws_iam as iam,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Optional


class FrontendStack(Stack):
    """Frontend hosting infrastructure stack"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        environment: str,
        domain_name: Optional[str] = None,
        certificate_arn: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        self.domain_name = domain_name
        self.certificate_arn = certificate_arn
        
        # Create S3 bucket for hosting
        self.hosting_bucket = self._create_hosting_bucket()
        
        # Create CloudFront distribution
        self.distribution = self._create_cloudfront_distribution()
        
        # Create Route53 records if domain is provided
        if self.domain_name and self.certificate_arn:
            self._create_dns_records()
        
        # Create deployment for initial content
        self._create_initial_deployment()
        
        # Create outputs
        self._create_outputs()
    
    def _create_hosting_bucket(self) -> s3.Bucket:
        """Create S3 bucket for frontend hosting"""
        bucket = s3.Bucket(
            self,
            "FrontendHostingBucket",
            bucket_name=f"tutor-system-frontend-{self.environment}-{self.account}",
            website_index_document="index.html",
            website_error_document="index.html",  # SPA routing
            public_read_access=False,  # CloudFront will handle access
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN,
            auto_delete_objects=self.environment == "development",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
        )
        
        # Add CORS configuration for API calls
        bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.POST, s3.HttpMethods.PUT, s3.HttpMethods.DELETE],
            allowed_origins=["*"],  # Will be restricted by CloudFront
            allowed_headers=["*"],
            max_age=3000
        )
        
        return bucket
    
    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution for global content delivery"""
        
        # Create Origin Access Control for S3
        oac = cloudfront.OriginAccessControl(
            self,
            "FrontendOAC",
            origin_access_control_name=f"tutor-system-frontend-oac-{self.environment}",
            description="Origin Access Control for frontend S3 bucket",
            origin_access_control_origin_type=cloudfront.OriginAccessControlOriginType.S3,
            signing_behavior=cloudfront.SigningBehavior.ALWAYS,
            signing_protocol=cloudfront.SigningProtocol.SIGV4
        )
        
        # Create cache policies
        spa_cache_policy = cloudfront.CachePolicy(
            self,
            "SPACachePolicy",
            cache_policy_name=f"tutor-system-spa-cache-{self.environment}",
            comment="Cache policy for SPA with API forwarding",
            default_ttl=Duration.hours(24),
            max_ttl=Duration.days(365),
            min_ttl=Duration.seconds(0),
            cookie_behavior=cloudfront.CacheCookieBehavior.none(),
            header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
                "Authorization", "Content-Type", "Accept", "Origin", "Referer"
            ),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            enable_accept_encoding_gzip=True,
            enable_accept_encoding_brotli=True
        )
        
        # Create origin request policy for API forwarding
        api_origin_request_policy = cloudfront.OriginRequestPolicy(
            self,
            "APIOriginRequestPolicy",
            origin_request_policy_name=f"tutor-system-api-origin-{self.environment}",
            comment="Origin request policy for API Gateway forwarding",
            cookie_behavior=cloudfront.OriginRequestCookieBehavior.none(),
            header_behavior=cloudfront.OriginRequestHeaderBehavior.allow_list(
                "Authorization", "Content-Type", "Accept", "Origin", "Referer", "User-Agent"
            ),
            query_string_behavior=cloudfront.OriginRequestQueryStringBehavior.all()
        )
        
        # Create response headers policy for security
        response_headers_policy = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeadersPolicy",
            response_headers_policy_name=f"tutor-system-security-headers-{self.environment}",
            comment="Security headers for frontend application",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.seconds(31536000),
                    include_subdomains=True,
                    preload=True
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(
                    override=True
                ),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY,
                    override=True
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                    override=True
                )
            ),
            custom_headers_behavior=cloudfront.ResponseCustomHeadersBehavior(
                custom_headers=[
                    cloudfront.ResponseCustomHeader(
                        header="X-Content-Type-Options",
                        value="nosniff",
                        override=True
                    ),
                    cloudfront.ResponseCustomHeader(
                        header="X-XSS-Protection",
                        value="1; mode=block",
                        override=True
                    ),
                    cloudfront.ResponseCustomHeader(
                        header="Permissions-Policy",
                        value="geolocation=(), microphone=(), camera=()",
                        override=True
                    )
                ]
            )
        )
        
        # Configure certificate if provided
        viewer_certificate = None
        domain_names = None
        
        if self.domain_name and self.certificate_arn:
            certificate = acm.Certificate.from_certificate_arn(
                self, "SSLCertificate", self.certificate_arn
            )
            viewer_certificate = cloudfront.ViewerCertificate.from_acm_certificate(
                certificate,
                aliases=[self.domain_name],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
                ssl_method=cloudfront.SSLMethod.SNI
            )
            domain_names = [self.domain_name]
        else:
            viewer_certificate = cloudfront.ViewerCertificate.from_cloudfront_default_certificate()
        
        # Create the distribution
        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.hosting_bucket,
                    origin_access_control=oac
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=spa_cache_policy,
                response_headers_policy=response_headers_policy,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                compress=True
            ),
            additional_behaviors={
                # API Gateway proxy behavior
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        f"api-{self.environment}.know-it-all-tutor.com",  # Replace with actual API Gateway domain
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=api_origin_request_policy,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD
                ),
                # Static assets with long-term caching
                "/assets/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(
                        self.hosting_bucket,
                        origin_access_control=oac
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                    response_headers_policy=response_headers_policy,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                    compress=True
                )
            },
            domain_names=domain_names,
            certificate=viewer_certificate,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            default_root_object="index.html",
            enable_ipv6=True,
            price_class=cloudfront.PriceClass.PRICE_CLASS_100 if self.environment == "development" else cloudfront.PriceClass.PRICE_CLASS_ALL,
            comment=f"Know-It-All Tutor Frontend Distribution - {self.environment}"
        )
        
        # Grant CloudFront access to S3 bucket
        self.hosting_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.hosting_bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{distribution.distribution_id}"
                    }
                }
            )
        )
        
        return distribution
    
    def _create_dns_records(self):
        """Create Route53 DNS records for custom domain"""
        if not self.domain_name:
            return
        
        # Get hosted zone (assumes it exists)
        hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=self.domain_name.split('.', 1)[1]  # Get root domain
        )
        
        # Create A record pointing to CloudFront
        route53.ARecord(
            self,
            "FrontendARecord",
            zone=hosted_zone,
            record_name=self.domain_name,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            ),
            ttl=Duration.minutes(5)
        )
        
        # Create AAAA record for IPv6
        route53.AaaaRecord(
            self,
            "FrontendAAAARecord",
            zone=hosted_zone,
            record_name=self.domain_name,
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.distribution)
            ),
            ttl=Duration.minutes(5)
        )
    
    def _create_initial_deployment(self):
        """Create initial deployment with placeholder content"""
        
        # Create a simple index.html for initial deployment
        initial_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Know-It-All Tutor - Loading...</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top: 4px solid white;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h1>Know-It-All Tutor</h1>
        <p>Preparing your learning experience...</p>
        <p><small>Environment: """ + self.environment + """</small></p>
    </div>
</body>
</html>"""
        
        # Deploy initial content
        s3_deployment.BucketDeployment(
            self,
            "InitialDeployment",
            sources=[s3_deployment.Source.data("index.html", initial_content)],
            destination_bucket=self.hosting_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
            prune=False  # Don't delete existing files
        )
    
    def _create_outputs(self):
        """Create CloudFormation outputs"""
        cdk.CfnOutput(
            self,
            "FrontendBucketName",
            value=self.hosting_bucket.bucket_name,
            description="S3 bucket name for frontend hosting"
        )
        
        cdk.CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront distribution ID"
        )
        
        cdk.CfnOutput(
            self,
            "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront distribution domain name"
        )
        
        if self.domain_name:
            cdk.CfnOutput(
                self,
                "FrontendURL",
                value=f"https://{self.domain_name}",
                description="Frontend application URL"
            )
        else:
            cdk.CfnOutput(
                self,
                "FrontendURL",
                value=f"https://{self.distribution.distribution_domain_name}",
                description="Frontend application URL"
            )