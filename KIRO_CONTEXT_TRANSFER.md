# KIRO CONTEXT TRANSFER - AI Tutor System
**Date:** 2026-02-19
**Location:** /home/jimbob/Dev/AWS_Dev (native Linux box)
**Previous Location:** /home/jimbob/ai-tutor-system (Windows laptop WSL2)

## PROJECT OVERVIEW
AI Tutor System - Multi-stack serverless application for interactive learning with quiz engine and ML-powered answer evaluation.

**Live Environment:**
- Frontend: https://d3awlgby2429wc.cloudfront.net
- API: https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod/
- Cognito User Pool: us-east-1_Bg1FA4097
- Admin User: huschlej@comcast.net (in admin group)

## ARCHITECTURE
**Multi-stack CDK deployment (6 stacks):**
1. NetworkStack-dev - VPC vpc-093fe5083f468ecc7
2. DatabaseStack-dev - RDS + DB Proxy Lambda
3. AuthStack-dev - Cognito
4. BackendStack-dev - API Gateway + Lambda functions
5. FrontendStack-dev - S3 + CloudFront
6. MonitoringStack-dev - CloudWatch

**Key Technical Details:**
- All Lambdas use DB Proxy (not direct database connections)
- DB Proxy Function: BackendStack-dev-DBProxyFunction9188AB04-tTKiBiDWe6Ww
- GitHub Actions CI/CD pipeline auto-deploys on push to main
- Repository: git@github.com:huschlej111/ai-tutor-system.git

## RECENT WORK (Last 24 hours)

### Yesterday (Hospital - Windows WSL2)
**Major fixes completed:**
1. User registration - Added PostConfirmation trigger to create database records
2. CORS errors - Fixed API Gateway error responses
3. Lambda imports - Removed shared. prefix from all handlers
4. Batch upload - Added missing Lambda/API routes, refactored to use DB Proxy
5. Admin access - Created Cognito groups, added user to admin

**Key Achievement:** Completed full batch upload refactor from transaction-based direct DB access to DB Proxy individual queries (203 lines refactored in process_batch_upload_transaction function).

### Today (Native Linux Box)
**Features implemented:**

#### 1. Public Domains (COMPLETED & DEPLOYED)
**Problem:** Admin batch uploads created domains only admin could see. Users couldn't quiz on centrally-managed content.

**Solution:** Added is_public column to tree_nodes table
- Migration: database/migrations/003_add_public_domains.sql
- Applied via: scripts/apply_public_domains_migration.py
- Updated queries: WHERE (user_id = %s OR is_public = true)
- Batch uploads now set is_public = true
- Quiz engine allows access to public domains

**Files Modified:**
- src/lambda_functions/batch_upload/handler.py
- src/lambda_functions/domain_management/handler.py
- src/lambda_functions/quiz_engine/handler.py

**Status:** ✅ Migration applied, code deployed

#### 2. Term Merging (COMPLETED & DEPLOYED)
**Problem:** Re-uploading larger datasets with overlapping content would skip entire domains, losing new terms.

**Solution:** Intelligent term merging
- Checks if domain exists (by name, including public domains)
- If exists: Gets existing terms, adds only NEW ones (case-insensitive)
- If new: Creates domain with all terms
- Skips duplicate terms within domain
- Updates term count accurately
- Provides detailed summary: "Merged 15 new terms, skipped 5 duplicates"

**Files Modified:**
- src/lambda_functions/batch_upload/handler.py (lines 420-540 refactored)

**Status:** ✅ Code committed and deployed

## CURRENT STATE

### Database Schema
```sql
CREATE TABLE tree_nodes (
  id UUID PRIMARY KEY,
  parent_id UUID REFERENCES tree_nodes(id),
  user_id UUID REFERENCES users(id) NOT NULL,
  node_type VARCHAR(50) NOT NULL, -- 'domain', 'term'
  data JSONB NOT NULL,
  metadata JSONB,
  is_public BOOLEAN DEFAULT false NOT NULL,  -- NEW
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_tree_nodes_public ON tree_nodes(is_public) WHERE is_public = true;
CREATE INDEX idx_tree_nodes_domain_access ON tree_nodes(node_type, user_id, is_public);
```

### Batch Upload Workflow
1. Admin uploads CSV/JSON via Admin Panel
2. System checks for existing domains (by name)
3. **If domain exists:**
   - Retrieves existing terms
   - Adds only new terms (skips duplicates)
   - Updates term count
   - Returns: "Merged X new terms, skipped Y duplicates"
4. **If domain is new:**
   - Creates domain with is_public = true
   - Adds all terms
   - Returns: "Created domain with X terms"
5. All users can now see and quiz on the content

### User Workflow
1. Regular user logs in
2. Views Domain Library (sees own domains + public domains)
3. Starts quiz on any accessible domain
4. Progress tracked per-user (even on shared content)

## PENDING WORK

### Immediate Testing Needed
1. Login as admin → Batch upload test domain
2. Login as regular user → Verify domain appears
3. Start quiz on public domain → Verify access works
4. Upload larger dataset with overlaps → Verify term merging

### Known Issues
None currently blocking.

### Future Enhancements (Documented, Not Urgent)
- 6 missing progress tracking functions (documented in tasks.md)
- Frontend tests (will use React Testing Library)
- Production environment rollout (out of scope)
- Domain versioning for updates
- User ratings/feedback on public domains

## TECHNICAL CONTEXT

### DB Proxy Pattern
```python
# All database access uses this pattern:
from db_proxy_client import DBProxyClient
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))

# Single query
result = db_proxy.execute_query(
    "SELECT * FROM users WHERE id = %s",
    params=[user_id],
    return_dict=True
)

# No transactions, no cursors, no context managers
# Each query is atomic
```

### Deployment Process
```bash
# Make changes
git add .
git commit -m "Description"
git push

# GitHub Actions automatically:
# 1. Runs tests (unit tests currently disabled in CI)
# 2. Synthesizes CDK stacks
# 3. Deploys to AWS (~5 min)
# 4. Updates all 6 stacks

# Monitor: https://github.com/huschlej111/ai-tutor-system/actions
```

### Migration Process
```bash
# Create migration SQL in database/migrations/
# Create Python script in scripts/ to apply via DB Proxy
# Run: python3 scripts/apply_migration_name.py
```

## USER CONTEXT
- Name: Jim (huschlej@comcast.net)
- Recovering from foot surgery
- Preparing for AWS SAP-C02 exam (1.5 months)
- Preference: Fix things properly, not shortcuts
- Working on native Linux box (transferred from Windows WSL2)

## SESSION NOTES
- Original session started on Windows laptop WSL2 (hospital)
- Context transferred to native Linux box
- Tool access issue: Command execution works in fresh sessions but not in transferred sessions
- Kiro CLI version: 1.26.2 (same on both systems)

## IMPORTANT FILES
- `.kiro/specs/ci-cd/tasks.md` - Project task tracking
- `.kiro/specs/ci-cd/POST_CONFIRMATION_TRIGGER_FIX.md` - User registration fix documentation
- `PUBLIC_DOMAINS_IMPLEMENTATION.md` - Public domains feature documentation
- `infrastructure/app_multistack.py` - Main CDK entry point
- `src/lambda_functions/batch_upload/handler.py` - Batch upload with term merging
- `database/migrations/003_add_public_domains.sql` - Latest migration

## NEXT STEPS
1. Wait for current deployment to complete (~5 min)
2. Test public domains feature
3. Test term merging with larger Python dataset
4. Verify end-to-end workflow works

## COMMANDS TO REMEMBER
```bash
# Activate venv
source venv/bin/activate

# Apply migration
python3 scripts/apply_migration_name.py

# Check deployment
# Visit: https://github.com/huschlej111/ai-tutor-system/actions

# Check Lambda update time
aws lambda get-function --function-name BackendStack-dev-BatchUploadFunctionEC7FA1F1-1b6KzD3XF3U1 --query 'Configuration.LastModified'
```

---
**Instructions for new session:**
Read this entire file to understand the project state, then continue from "NEXT STEPS" section.
