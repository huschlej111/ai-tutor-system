# Requirements Document: Quiz Engine and Answer Evaluation Deployment

## Introduction

This document specifies the requirements for deploying the Quiz Engine and Answer Evaluation system to AWS. The system enables users to take quizzes on their created domains and receive semantic evaluation of their answers using a machine learning model.

## Glossary

- **Quiz_Engine**: Lambda function that manages quiz sessions, question presentation, and session state
- **Answer_Evaluator**: Lambda function that evaluates student answers using semantic similarity
- **ML_Model_Layer**: Lambda layer containing sentence transformer model (~200MB)
- **Shared_Layer**: Existing Lambda layer with common utilities
- **DB_Proxy**: Existing Lambda function inside VPC that handles all database operations
- **Lambda_Bridge_Pattern**: Architecture where Lambda A (outside VPC) invokes Lambda B (inside VPC)
- **Quiz_Session**: A user's active, paused, or completed quiz attempt on a specific domain
- **Semantic_Similarity**: ML-based comparison of text meaning (0.0 to 1.0 score)
- **CDK_Stack**: AWS Cloud Development Kit infrastructure-as-code (auth_only_stack.py)
- **Cognito_Authorizer**: API Gateway authorizer that validates JWT tokens

## Requirements

### Requirement 1: Quiz Engine Lambda Deployment

**User Story:** As a DevOps engineer, I want to deploy the Quiz Engine Lambda function to AWS, so that users can start and manage quiz sessions through the API.

#### Acceptance Criteria

1.1. THE CDK_Stack SHALL create a Quiz_Engine Lambda function with Python 3.12 runtime
1.2. THE Quiz_Engine SHALL be configured with 256MB memory and 30-second timeout
1.3. THE Quiz_Engine SHALL be deployed outside the VPC
1.4. THE Quiz_Engine SHALL use the existing Shared_Layer
1.5. THE Quiz_Engine SHALL have environment variable DB_PROXY_FUNCTION_NAME
1.6. THE CDK_Stack SHALL grant Quiz_Engine permission to invoke DB_Proxy Lambda
1.7. THE Quiz_Engine SHALL integrate with existing Cognito_Authorizer

### Requirement 2: Answer Evaluation Lambda Deployment

**User Story:** As a DevOps engineer, I want to deploy the Answer Evaluation Lambda with ML model support.

#### Acceptance Criteria

2.1. THE CDK_Stack SHALL create an Answer_Evaluator Lambda with Python 3.12 runtime
2.2. THE Answer_Evaluator SHALL be configured with 512MB memory and 60-second timeout
2.3. THE Answer_Evaluator SHALL be deployed outside the VPC
2.4. THE Answer_Evaluator SHALL use both Shared_Layer and ML_Model_Layer
2.5. THE Answer_Evaluator SHALL have environment variable MODEL_PATH=/opt/ml_model
2.6. THE CDK_Stack SHALL grant Answer_Evaluator permission to invoke DB_Proxy
2.7. THE Answer_Evaluator SHALL integrate with Cognito_Authorizer

### Requirement 3: ML Model Layer Creation

**User Story:** As a DevOps engineer, I want to create a Lambda layer containing the sentence transformer model.

#### Acceptance Criteria

3.1. THE CDK_Stack SHALL create ML_Model_Layer from final_similarity_model directory
3.2. THE ML_Model_Layer SHALL package model files in /opt/ml_model structure
3.3. THE ML_Model_Layer SHALL include sentence-transformers, torch, scikit-learn
3.4. THE ML_Model_Layer SHALL be compatible with Python 3.12 runtime
3.5. THE System SHALL use S3 for layer storage when size exceeds 50MB
3.6. THE ML_Model_Layer SHALL be versioned for rollback support

### Requirement 4: API Gateway Routes for Quiz Operations

**User Story:** As a frontend developer, I want API endpoints for quiz operations.

#### Acceptance Criteria

4.1. THE CDK_Stack SHALL create /quiz resource under existing API Gateway
4.2. THE CDK_Stack SHALL create POST /quiz/start endpoint
4.3. THE CDK_Stack SHALL create POST /quiz/answer endpoint
4.4. THE CDK_Stack SHALL create GET /quiz/question endpoint
4.5. THE CDK_Stack SHALL create POST /quiz/pause endpoint
4.6. THE CDK_Stack SHALL create POST /quiz/resume endpoint
4.7. THE CDK_Stack SHALL create GET /quiz/session/{sessionId} endpoint
4.8. THE CDK_Stack SHALL create DELETE /quiz/session/{sessionId} endpoint
4.9. ALL quiz endpoints SHALL require Cognito_Authorizer authentication
4.10. THE CDK_Stack SHALL configure CORS for all quiz endpoints

### Requirement 5: API Gateway Routes for Answer Evaluation

**User Story:** As a frontend developer, I want API endpoints for answer evaluation.

#### Acceptance Criteria

5.1. THE CDK_Stack SHALL create POST /quiz/evaluate endpoint
5.2. THE CDK_Stack SHALL create POST /quiz/evaluate/batch endpoint
5.3. THE CDK_Stack SHALL create GET /quiz/evaluate/health endpoint
5.4. /quiz/evaluate endpoints SHALL require Cognito_Authorizer authentication
5.5. /quiz/evaluate/health SHALL allow unauthenticated access
5.6. THE CDK_Stack SHALL configure CORS for evaluate endpoints

### Requirement 6: Database Schema Validation

**User Story:** As a DevOps engineer, I want to validate database schema supports quiz operations.

#### Acceptance Criteria

6.1. THE System SHALL verify quiz_sessions table exists in RDS
6.2. THE System SHALL verify progress_records table exists in RDS
6.3. THE System SHALL verify tree_nodes table has required indexes
6.4. THE System SHALL provide clear error messages if tables are missing
6.5. THE System SHALL validate DB_Proxy has permissions for quiz tables

### Requirement 7: Lambda Integration Testing

**User Story:** As a DevOps engineer, I want to test Lambda integrations after deployment.

#### Acceptance Criteria

7.1. THE System SHALL provide test commands for quiz operations
7.2. Tests SHALL verify Quiz_Engine can start a quiz session
7.3. Tests SHALL verify Quiz_Engine can submit and evaluate answers
7.4. Tests SHALL verify Answer_Evaluator calculates semantic similarity
7.5. Tests SHALL verify DB_Proxy integration stores progress records
7.6. THE System SHALL provide diagnostic information when tests fail

### Requirement 8: Deployment Rollback Capability

**User Story:** As a DevOps engineer, I want rollback capability for deployment issues.

#### Acceptance Criteria

8.1. THE CDK_Stack SHALL tag all resources with deployment version
8.2. THE System SHALL maintain previous Lambda function versions
8.3. THE System SHALL support reverting API Gateway integrations
8.4. THE System SHALL support reverting Lambda layer versions
8.5. THE System SHALL preserve database state during rollback

### Requirement 9: Cost Optimization

**User Story:** As a system administrator, I want to remain within AWS free tier limits.

#### Acceptance Criteria

9.1. THE Quiz_Engine SHALL use 256MB memory (free tier)
9.2. THE Answer_Evaluator SHALL use 512MB memory (minimum for ML)
9.3. THE System SHALL reuse existing VPC, RDS, Cognito resources
9.4. THE System SHALL not create NAT Gateways or expensive resources
9.5. THE CDK_Stack SHALL output estimated monthly costs
9.6. THE System SHALL configure Lambda concurrency limits

### Requirement 10: Monitoring and Logging

**User Story:** As a DevOps engineer, I want comprehensive logging and monitoring.

#### Acceptance Criteria

10.1. THE Quiz_Engine SHALL log session state transitions to CloudWatch
10.2. THE Answer_Evaluator SHALL log evaluation requests with scores
10.3. THE System SHALL create CloudWatch log groups with 7-day retention
10.4. THE CDK_Stack SHALL create alarms for Lambda errors
10.5. THE CDK_Stack SHALL create alarms for Lambda duration
10.6. THE System SHALL output CloudWatch dashboard URL

### Requirement 11: Security and Access Control

**User Story:** As a security engineer, I want proper security controls.

#### Acceptance Criteria

11.1. THE Quiz_Engine SHALL validate users access only their own sessions
11.2. THE Answer_Evaluator SHALL validate authenticated requests
11.3. THE System SHALL use IAM roles with least-privilege permissions
11.4. THE Quiz_Engine SHALL not expose database credentials
11.5. THE Answer_Evaluator SHALL not expose ML model internals
11.6. THE System SHALL encrypt data in transit using HTTPS/TLS
11.7. THE System SHALL use existing RDS encryption at rest

### Requirement 12: Frontend Integration Support

**User Story:** As a frontend developer, I want clear API documentation.

#### Acceptance Criteria

12.1. THE System SHALL output API Gateway URL for quiz endpoints
12.2. THE System SHALL output example API requests
12.3. THE System SHALL provide OpenAPI/Swagger documentation
12.4. THE System SHALL document required request headers
12.5. THE System SHALL document response codes and error messages
12.6. THE System SHALL provide example frontend code snippets

### Requirement 13: Incremental Deployment Strategy

**User Story:** As a DevOps engineer, I want to deploy incrementally.

#### Acceptance Criteria

13.1. THE System SHALL support deploying Quiz_Engine independently
13.2. THE System SHALL support deploying Answer_Evaluator independently
13.3. THE Quiz_Engine SHALL use fallback similarity when Answer_Evaluator unavailable
13.4. THE System SHALL support deploying ML_Model_Layer first
13.5. THE System SHALL validate dependencies before each phase
13.6. THE System SHALL provide deployment phase documentation
