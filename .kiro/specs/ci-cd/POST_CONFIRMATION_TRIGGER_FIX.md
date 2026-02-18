# User Registration Fix - PostConfirmation Trigger

## Problem
When users registered via the frontend (using Cognito SDK directly), they were created in Cognito but NOT in the database. This caused 404 errors when trying to access dashboard/domains because the Lambda functions couldn't find the user record.

## Root Cause
The frontend uses AWS Amplify/Cognito SDK to register users directly with Cognito, bypassing the `/auth/register` API endpoint. The auth Lambda's register handler (which creates the database record) was never called.

## Solution
Added a Cognito **PostConfirmation trigger** that automatically creates a user record in the database after successful Cognito registration.

## Implementation Details

### 1. Created PostConfirmation Lambda
**File:** `src/lambda_functions/cognito_triggers/post_confirmation.py`

This Lambda:
- Receives Cognito trigger event after user confirms registration
- Extracts user attributes (cognito_sub, email, first_name, last_name)
- Calls DB Proxy to insert user record into database
- Uses `ON CONFLICT DO NOTHING` to handle duplicates gracefully

### 2. Cross-Stack Dependency Challenge
**Problem:** 
- AuthStack creates the Cognito User Pool
- BackendStack has the DB Proxy Lambda and shared layer
- PostConfirmation trigger needs both

**Solution:** Created the PostConfirmation Lambda in BackendStack, then used a CDK Custom Resource to automatically wire it to the Cognito User Pool.

### 3. Custom Resource for Automatic Configuration
**File:** `infrastructure/stacks/backend_stack.py`

Created a custom Lambda that:
- Updates the Cognito User Pool's LambdaConfig
- Adds both PreSignUp and PostConfirmation triggers
- Runs automatically during CDK deployment (no manual steps!)

### 4. Key Code Changes

**PostConfirmation Lambda:**
```python
# Extracts user info from Cognito event
cognito_sub = event.get('userName')  # This is the Cognito sub
email = user_attributes.get('email')

# Creates user in database via DB Proxy
db_proxy.execute_query(
    """
    INSERT INTO users (cognito_sub, email, first_name, last_name, is_active)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (cognito_sub) DO NOTHING
    """,
    params=[cognito_sub, email, first_name, last_name, True]
)
```

**Custom Resource (inline Lambda):**
```python
# Updates Cognito User Pool with both triggers
cognito.update_user_pool(
    UserPoolId=user_pool_id,
    LambdaConfig={
        'PreSignUp': pre_signup_arn,
        'PostConfirmation': post_confirmation_arn
    }
)
```

## Testing
1. Delete all test users from Cognito and database
2. Register a new user via the UI
3. Verify user exists in both Cognito AND database
4. Login and access dashboard - should work!

## Prevention for Next Time

### Checklist for New Cognito User Pools:
- [ ] Create PostConfirmation trigger Lambda
- [ ] Wire trigger to User Pool (via CDK Custom Resource)
- [ ] Test registration flow end-to-end
- [ ] Verify user created in both Cognito and database

### Common Pitfalls:
1. **Import paths:** Lambda layer modules are in `/opt/python/`, not `/opt/python/shared/`
2. **Cross-stack dependencies:** Use Custom Resources to wire resources across stacks
3. **Testing:** Always test with a fresh user registration, not just login

### Related Files:
- `src/lambda_functions/cognito_triggers/post_confirmation.py` - Trigger Lambda
- `infrastructure/stacks/backend_stack.py` - Custom Resource configuration
- `infrastructure/stacks/auth_stack.py` - User Pool definition
- `scripts/cleanup_test_users.py` - Test user cleanup script

## Time Investment
- Initial issue: ~3 hours debugging 404 errors
- Root cause identification: ~30 minutes
- Implementation: ~2 hours (multiple deployment failures due to CDK syntax)
- Total: ~5.5 hours

## Lessons Learned
1. **Frontend registration bypasses API:** When using Cognito SDK directly, API handlers aren't called
2. **Cognito triggers are essential:** PostConfirmation trigger is the right place to create database records
3. **CDK Custom Resources are powerful:** They enable cross-stack automation without manual steps
4. **Test early:** Should have tested registration immediately after stack separation
