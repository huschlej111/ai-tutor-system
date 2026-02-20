#!/bin/bash
cd /home/jimbob/Dev/AWS_Dev

git add src/lambda_functions/batch_upload/handler.py

git commit -m "Add term merging for batch uploads

When uploading domains that already exist, the system now:
- Keeps the existing domain
- Adds only NEW terms (skips duplicates by term name)
- Updates term count metadata
- Provides detailed summary of merge results

This allows uploading larger datasets that include previously
uploaded content without losing new terms or creating duplicates."

git push
