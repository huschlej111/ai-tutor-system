# Implementation Tasks: Quiz Engine and Answer Evaluation Deployment

## Overview
This task list implements the Quiz Engine and Answer Evaluation system deployment as specified in `kiro-specs/quiz-engine-deployment/requirements.md`. The implementation follows an incremental deployment strategy with 5 phases to minimize risk and enable rollback.

---

## Phase 1: ML Model Layer Deployment

### Task 1.1: Create ML Model Layer Build Script
- [ ] Create `scripts/build_ml_layer.sh` script
- [ ] Implement directory structure creation (layer/ml_model, layer/python)
- [ ] Add model file copying from final_similarity_model/
- [ ] Add Python dependency installation (sentence-transformers==2.2.2, torch==2.0.1, transformers==4.30.2, scikit-learn==1.3.0, numpy==1.24.3)
- [ ] Add zip file creation logic
- [ ] Add S3 upload command for layers >50MB
- [ ] Add Lambda layer version publishing command
- [ ] Make script executable (chmod +x)

**Validates:** Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

### Task 1.2: Build and Deploy ML Model Layer
- [ ] Run build_ml_layer.sh script
- [ ] Verify layer size is ~200MB
- [ ] Verify S3 upload successful
- [ ] Verify Lambda layer version published
- [ ] Record layer ARN for use in CDK stack
- [ ] Test layer can be attached to Python 3.12 Lambda

**Validates:** Requirements 3.1, 3.5, 3.6

---

## Phase 2: Database Schema Migration

### Task 2.1: Create Database Migration Script
- [ ] Create `scripts/migrate_quiz_schema.py` script
- [ ] Implement QuizSchemaMigration class with __init__ method
- [ ] Implement validate_schema() method to check for quiz_sessions table
- [ ] Implement validate_schema() method to check for progress_records table
- [ ] Implement validate_schema() method to check for tree_nodes indexes
- [ ] Implement apply_migration() method to create quiz_sessions table
- [ ] Implement apply_migration() method to create progress_records table
- [ ] Implement apply_migration() method to create all required indexes
- [ ] Implement verify_db_proxy_permissions() method
- [ ] Add error handling and rollback logic
- [ ] Add clear error messages for missing components

**Validates:** Requirements 6.1, 6.2, 6.3, 6.4, 6.5

### Task 2.2: Execute Database Migration
- [ ] Run migration script in validation mode (--validate)
- [ ] Review validation results
- [ ] Run migration script in apply mode (--apply)
- [ ] Verify quiz_sessions table created with correct schema
- [ ] Verify progress_records table created with correct schema
- [ ] Verify all indexes created successfully
- [ ] Verify DB Proxy has permissions for quiz tables
- [ ] Document migration results

**Validates:** Requirements 6.1, 6.2, 6.3, 6.5

---

## Phase 3: Answer Evaluator Lambda Deployment

### Task 3.1: Implement Answer Evaluator Handler
- [ ] Create `src/lambda_functions/answer_evaluator/handler.py`
- [ ] Implement AnswerEvaluator class with __init__ method
- [ ] Implement _load_model() method to load sentence transformer from /opt/ml_model
- [ ] Implement evaluate_answer() method with text encoding and cosine similarity
- [ ] Implement batch_evaluate() method for multiple answer pairs
- [ ] Implement health_check() method to verify model loaded
- [ ] Implement _generate_feedback() method with graduated feedback (>=threshold, 0.6-threshold, <0.6)
- [ ] Implement main() Lambda handler function
- [ ] Add request validation and error handling
- [ ] Add structured logging for evaluation requests

**Validates:** Requirements 2.1, 2.2, 2.4, 2.5, 7.4, 10.2

### Task 3.2: Create Answer Evaluator Lambda in CDK Stack
- [ ] Open `infrastructure/stacks/auth_only_stack.py`
- [ ] Add _create_answer_evaluator_lambda() method
- [ ] Configure Lambda with Python 3.12 runtime
- [ ] Set memory to 512MB and timeout to 60 seconds
- [ ] Deploy outside VPC
- [ ] Attach Shared Layer and ML Model Layer
- [ ] Set environment variables (MODEL_PATH, SIMILARITY_THRESHOLD, DB_PROXY_FUNCTION_NAME, LOG_LEVEL)
- [ ] Grant permission to invoke DB Proxy Lambda
- [ ] Add CloudWatch Logs permissions
- [ ] Call method from __init__

**Validates:** Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

### Task 3.3: Test Answer Evaluator Lambda
- [ ] Deploy CDK stack with Answer Evaluator
- [ ] Invoke health_check endpoint
- [ ] Verify model loads successfully
- [ ] Test evaluate_answer with sample inputs
- [ ] Verify similarity scores in range [0.0, 1.0]
- [ ] Verify feedback generation works correctly
- [ ] Test batch_evaluate with multiple answer pairs
- [ ] Verify CloudWatch logs contain evaluation requests

**Validates:** Requirements 2.7, 5.3, 7.4, 10.2

---

## Phase 4: Quiz Engine Lambda Deployment

### Task 4.1: Extend DB Proxy with Quiz Operations
- [ ] Open existing DB Proxy handler file
- [ ] Implement create_quiz_session(session_data) method
- [ ] Implement get_quiz_session(session_id) method
- [ ] Implement update_quiz_session(session_id, updates) method
- [ ] Implement delete_quiz_session(session_id) method
- [ ] Implement get_domain_terms(domain_id) method
- [ ] Implement record_progress(progress_data) method
- [ ] Implement get_user_progress(user_id, domain_id) method
- [ ] Add error handling for database operations
- [ ] Deploy updated DB Proxy Lambda

**Validates:** Requirements 1.6, 2.6, 6.5, 7.5

### Task 4.2: Implement Quiz Engine Handler
- [ ] Create `src/lambda_functions/quiz_engine/handler.py`
- [ ] Implement QuizEngine class with __init__ method
- [ ] Implement start_quiz(user_id, domain_id) method
- [ ] Implement get_next_question(session_id) method
- [ ] Implement submit_answer(session_id, term_id, student_answer) method
- [ ] Implement pause_quiz(session_id) method
- [ ] Implement resume_quiz(session_id) method
- [ ] Implement get_session(session_id) method
- [ ] Implement delete_session(session_id) method
- [ ] Implement main() Lambda handler function
- [ ] Add session ownership validation
- [ ] Add domain access validation
- [ ] Add request validation
- [ ] Add structured logging for session state transitions

**Validates:** Requirements 1.1, 1.5, 1.6, 7.2, 7.3, 10.1, 11.1

### Task 4.3: Implement Security Validation
- [ ] Create `src/lambda_functions/quiz_engine/security.py`
- [ ] Implement SessionSecurityValidator class
- [ ] Implement validate_session_ownership(session_id, user_id) method
- [ ] Implement validate_domain_access(domain_id, user_id) method
- [ ] Add error handling for unauthorized access
- [ ] Integrate security validation into Quiz Engine handler

**Validates:** Requirements 11.1, 11.2, 11.4

### Task 4.4: Implement Request Validation
- [ ] Create `src/lambda_functions/quiz_engine/validation.py`
- [ ] Implement RequestValidator class
- [ ] Implement validate_start_quiz_request(body) method
- [ ] Implement validate_submit_answer_request(body) method
- [ ] Implement validate_evaluate_request(body) method
- [ ] Add UUID validation
- [ ] Add answer length validation (max 1000 characters)
- [ ] Add threshold validation (0.0 to 1.0)
- [ ] Integrate request validation into Quiz Engine handler

**Validates:** Requirements 11.2, 11.4

### Task 4.5: Create Quiz Engine Lambda in CDK Stack
- [ ] Open `infrastructure/stacks/auth_only_stack.py`
- [ ] Add _create_quiz_engine_lambda() method
- [ ] Configure Lambda with Python 3.12 runtime
- [ ] Set memory to 256MB and timeout to 30 seconds
- [ ] Deploy outside VPC
- [ ] Attach Shared Layer
- [ ] Set environment variables (DB_PROXY_FUNCTION_NAME, LOG_LEVEL, REGION)
- [ ] Grant permission to invoke DB Proxy Lambda
- [ ] Grant permission to invoke Answer Evaluator Lambda
- [ ] Add CloudWatch Logs permissions
- [ ] Call method from __init__

**Validates:** Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6

### Task 4.6: Test Quiz Engine Lambda
- [ ] Deploy CDK stack with Quiz Engine
- [ ] Test start_quiz endpoint with valid domain_id
- [ ] Verify quiz session created in database
- [ ] Test get_next_question endpoint
- [ ] Verify question returned with correct format
- [ ] Test submit_answer endpoint
- [ ] Verify Answer Evaluator invoked successfully
- [ ] Verify progress recorded in database
- [ ] Test pause_quiz and resume_quiz endpoints
- [ ] Test get_session and delete_session endpoints
- [ ] Verify CloudWatch logs contain session state transitions

**Validates:** Requirements 1.7, 7.2, 7.3, 7.5, 10.1

---

## Phase 5: API Gateway Integration

### Task 5.1: Create Quiz Operations API Routes
- [ ] Open `infrastructure/stacks/auth_only_stack.py`
- [ ] Add _create_quiz_api_routes() method
- [ ] Create /quiz resource under existing API Gateway
- [ ] Create POST /quiz/start endpoint with Lambda integration
- [ ] Create GET /quiz/question endpoint with Lambda integration
- [ ] Create POST /quiz/answer endpoint with Lambda integration
- [ ] Create POST /quiz/pause endpoint with Lambda integration
- [ ] Create POST /quiz/resume endpoint with Lambda integration
- [ ] Create GET /quiz/session/{sessionId} endpoint with Lambda integration
- [ ] Create DELETE /quiz/session/{sessionId} endpoint with Lambda integration
- [ ] Attach Cognito authorizer to all quiz endpoints
- [ ] Configure CORS for all quiz endpoints
- [ ] Call method from __init__

**Validates:** Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10

### Task 5.2: Create Answer Evaluation API Routes
- [ ] Open `infrastructure/stacks/auth_only_stack.py`
- [ ] Add _create_evaluation_api_routes() method
- [ ] Create POST /quiz/evaluate endpoint with Lambda integration
- [ ] Create POST /quiz/evaluate/batch endpoint with Lambda integration
- [ ] Create GET /quiz/evaluate/health endpoint with Lambda integration
- [ ] Attach Cognito authorizer to /quiz/evaluate and /quiz/evaluate/batch
- [ ] Leave /quiz/evaluate/health without authentication
- [ ] Configure CORS for all evaluation endpoints
- [ ] Call method from __init__

**Validates:** Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6

### Task 5.3: Deploy API Gateway Changes
- [ ] Deploy CDK stack with API Gateway routes
- [ ] Verify all routes created successfully
- [ ] Verify Cognito authorizer attached to protected routes
- [ ] Verify CORS configured correctly
- [ ] Record API Gateway URL for testing
- [ ] Test unauthenticated request to protected route (should return 401)
- [ ] Test authenticated request to protected route (should succeed)

**Validates:** Requirements 4.9, 4.10, 5.4, 5.5, 5.6, 11.2, 11.6

---

## Phase 6: Monitoring and Logging

### Task 6.1: Create CloudWatch Monitoring Configuration
- [ ] Create `infrastructure/monitoring/quiz_monitoring.py`
- [ ] Implement QuizMonitoring class with __init__ method
- [ ] Create SNS topic for alerts
- [ ] Implement _create_lambda_metrics() method for Quiz Engine
- [ ] Implement _create_lambda_metrics() method for Answer Evaluator
- [ ] Implement _create_alarms() method for Quiz Engine error rate
- [ ] Implement _create_alarms() method for Quiz Engine duration
- [ ] Implement _create_alarms() method for Answer Evaluator error rate
- [ ] Implement _create_alarms() method for Answer Evaluator duration
- [ ] Implement _create_dashboard() method with all metrics
- [ ] Integrate monitoring into CDK stack

**Validates:** Requirements 10.3, 10.4, 10.5, 10.6

### Task 6.2: Implement Structured Logging
- [ ] Create `src/lambda_functions/quiz_engine/logger.py`
- [ ] Implement QuizLogger class with __init__ method
- [ ] Implement log_session_event() method for state transitions
- [ ] Implement log_evaluation() method for answer evaluations
- [ ] Implement log_error() method with context
- [ ] Integrate logger into Quiz Engine handler
- [ ] Integrate logger into Answer Evaluator handler
- [ ] Configure CloudWatch log groups with 7-day retention

**Validates:** Requirements 10.1, 10.2, 10.3

### Task 6.3: Deploy Monitoring Configuration
- [ ] Deploy CDK stack with monitoring configuration
- [ ] Verify CloudWatch log groups created
- [ ] Verify CloudWatch alarms created
- [ ] Verify CloudWatch dashboard created
- [ ] Verify SNS topic created for alerts
- [ ] Test alarm triggers with simulated errors
- [ ] Record CloudWatch dashboard URL

**Validates:** Requirements 10.4, 10.5, 10.6

---

## Phase 7: Testing and Validation

### Task 7.1: Create Integration Test Script
- [ ] Create `scripts/test_quiz_deployment.py`
- [ ] Implement QuizDeploymentTests class with __init__ method
- [ ] Implement authenticate() method for Cognito authentication
- [ ] Implement test_start_quiz() method
- [ ] Implement test_get_question() method
- [ ] Implement test_submit_answer() method
- [ ] Implement test_pause_resume_quiz() method
- [ ] Implement test_answer_evaluator_health() method
- [ ] Implement test_semantic_evaluation() method with test cases
- [ ] Implement test_db_proxy_integration() method
- [ ] Implement run_all_tests() method
- [ ] Add diagnostic information for test failures

**Validates:** Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6

### Task 7.2: Execute Integration Tests
- [ ] Run test_quiz_deployment.py script
- [ ] Verify all tests pass
- [ ] Review test output for any warnings
- [ ] Fix any issues identified by tests
- [ ] Re-run tests to confirm fixes
- [ ] Document test results

**Validates:** Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6

### Task 7.3: Create Property-Based Tests
- [ ] Create `tests/property_tests/test_quiz_properties.py`
- [ ] Implement QuizSessionStateMachine for state testing
- [ ] Implement test_evaluation_consistency property test
- [ ] Implement test_evaluation_symmetry property test
- [ ] Implement test_session_persistence_round_trip property test
- [ ] Implement test_progress_calculation_monotonicity property test
- [ ] Run property-based tests with 100+ examples
- [ ] Verify all properties hold

**Validates:** Requirements 7.1, 7.4

---

## Phase 8: Security and IAM Configuration

### Task 8.1: Create IAM Policies
- [ ] Create `infrastructure/security/quiz_iam_policies.py`
- [ ] Implement QuizIAMPolicies class
- [ ] Implement create_quiz_engine_policy() method (least-privilege)
- [ ] Implement create_answer_evaluator_policy() method (least-privilege)
- [ ] Implement create_cloudwatch_logs_policy() method
- [ ] Integrate IAM policies into CDK stack
- [ ] Verify Lambda functions have only required permissions

**Validates:** Requirements 11.3, 11.4, 11.5

### Task 8.2: Configure Encryption
- [ ] Verify HTTPS/TLS enabled on API Gateway
- [ ] Verify RDS encryption at rest enabled
- [ ] Verify CloudWatch Logs encryption enabled
- [ ] Verify S3 bucket encryption enabled for ML model layer
- [ ] Document encryption configuration

**Validates:** Requirements 11.6, 11.7

---

## Phase 9: Cost Optimization

### Task 9.1: Configure Lambda Concurrency Limits
- [ ] Open `infrastructure/stacks/auth_only_stack.py`
- [ ] Add _configure_concurrency_limits() method
- [ ] Set Quiz Engine reserved concurrent executions to 10
- [ ] Set Answer Evaluator reserved concurrent executions to 5
- [ ] Call method from __init__
- [ ] Deploy CDK stack with concurrency limits

**Validates:** Requirement 9.6

### Task 9.2: Create Cost Monitoring Script
- [ ] Create `scripts/monitor_costs.py`
- [ ] Implement CostMonitor class with __init__ method
- [ ] Implement get_monthly_costs() method using Cost Explorer API
- [ ] Implement check_free_tier_usage() method for Lambda, API Gateway, RDS
- [ ] Implement _get_lambda_invocations() method
- [ ] Implement _get_lambda_compute_time() method
- [ ] Implement _get_api_gateway_requests() method
- [ ] Implement generate_cost_report() method
- [ ] Run cost monitoring script
- [ ] Verify costs within free tier limits

**Validates:** Requirements 9.1, 9.2, 9.3, 9.4, 9.5

---

## Phase 10: Deployment Rollback Capability

### Task 10.1: Create Rollback Script
- [ ] Create `scripts/rollback_quiz_deployment.py`
- [ ] Implement QuizDeploymentRollback class with __init__ method
- [ ] Implement rollback_lambda_functions() method
- [ ] Implement rollback_api_gateway() method
- [ ] Implement rollback_database_migration() method (conservative, preserves data)
- [ ] Add version tagging to all resources
- [ ] Test rollback procedure in non-production environment
- [ ] Document rollback procedures

**Validates:** Requirements 8.1, 8.2, 8.3, 8.4, 8.5

---

## Phase 11: Documentation and Frontend Integration

### Task 11.1: Create API Documentation
- [ ] Create `docs/api/quiz-endpoints.yaml` OpenAPI specification
- [ ] Document all quiz operation endpoints
- [ ] Document all answer evaluation endpoints
- [ ] Document request/response schemas
- [ ] Document authentication requirements
- [ ] Document error codes and messages
- [ ] Generate Swagger UI documentation

**Validates:** Requirements 12.3, 12.4, 12.5

### Task 11.2: Create Frontend Integration Examples
- [ ] Create `frontend/src/services/quizService.ts` API client
- [ ] Implement QuizService class with all API methods
- [ ] Create `frontend/src/components/QuizInterface.tsx` React component
- [ ] Implement quiz workflow UI (start, question, answer, pause, resume)
- [ ] Add error handling and loading states
- [ ] Create example code snippets for documentation
- [ ] Document API Gateway URL and authentication

**Validates:** Requirements 12.1, 12.2, 12.6

---

## Phase 12: Final Validation and Deployment

### Task 12.1: Execute End-to-End Test
- [ ] Start quiz session via API
- [ ] Get first question
- [ ] Submit answer and verify evaluation
- [ ] Get next question
- [ ] Pause quiz session
- [ ] Resume quiz session
- [ ] Complete quiz session
- [ ] Verify all progress recorded in database
- [ ] Verify CloudWatch logs contain all events
- [ ] Verify CloudWatch metrics updated

**Validates:** All requirements

### Task 12.2: Create Deployment Documentation
- [ ] Document deployment phases and sequence
- [ ] Document validation checklist for each phase
- [ ] Document rollback procedures
- [ ] Document monitoring and alerting setup
- [ ] Document cost optimization configuration
- [ ] Document troubleshooting guide
- [ ] Create deployment runbook

**Validates:** Requirement 13.6

### Task 12.3: Production Deployment
- [ ] Review all test results
- [ ] Review cost estimates
- [ ] Review security configuration
- [ ] Deploy to production environment
- [ ] Execute production validation tests
- [ ] Monitor CloudWatch metrics for 24 hours
- [ ] Document production deployment results

**Validates:** Requirements 13.1, 13.2, 13.3, 13.4, 13.5

---

## Deployment Validation Checklist

- [ ] ML Model Layer published and versioned
- [ ] Database schema migrated successfully
- [ ] Answer Evaluator Lambda created and health check passes
- [ ] Quiz Engine Lambda created and DB Proxy invocation works
- [ ] API Gateway routes created with Cognito authorizer
- [ ] CORS configured on all routes
- [ ] End-to-end test: start quiz → get question → submit answer → receive evaluation
- [ ] CloudWatch monitoring and alarms configured
- [ ] Rollback procedures documented and tested
- [ ] Cost estimates within free tier limits
- [ ] Security validation complete (IAM, encryption, access control)
- [ ] API documentation published
- [ ] Frontend integration examples provided

---

## Notes

- All tasks should be executed in the order specified
- Each phase should be validated before proceeding to the next
- Rollback capability should be tested before production deployment
- Cost monitoring should be performed after each phase
- Security validation should be performed throughout the deployment process
