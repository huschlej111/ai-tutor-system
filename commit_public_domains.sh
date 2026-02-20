#!/bin/bash
cd /home/jimbob/Dev/AWS_Dev

git add database/migrations/003_add_public_domains.sql
git add scripts/apply_public_domains_migration.py
git add src/lambda_functions/batch_upload/handler.py
git add src/lambda_functions/domain_management/handler.py
git add src/lambda_functions/quiz_engine/handler.py
git add PUBLIC_DOMAINS_IMPLEMENTATION.md

git commit -m "Add public domain sharing for batch uploads

Enables admin-uploaded domains to be shared with all users.

Changes:
- Added is_public column to tree_nodes table
- Batch uploads now create public domains (is_public=true)
- Domain queries include public domains: (user_id = X OR is_public = true)
- Quiz engine allows access to public domains
- Progress tracking remains per-user

Users can now take quizzes on admin-uploaded content without
creating personal copies. Fixes the content sharing workflow."

git push
