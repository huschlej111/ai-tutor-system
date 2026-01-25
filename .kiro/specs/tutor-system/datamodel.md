# Data Model Documentation

## Overview

The Know-It-All Tutor system uses PostgreSQL with JSONB for its data persistence layer, implementing a Domain-Agnostic Tree Data Model that separates content structure from domain-specific payloads. This approach enables the system to handle any knowledge domain without code changes while maintaining relational integrity and rich query capabilities.

## Database Technology Decision

### PostgreSQL with JSONB - Final Choice

After evaluating multiple database technologies against system requirements, PostgreSQL with JSONB was selected as the optimal solution.

#### Alternatives Considered

1. **DynamoDB (AWS Always Free)**
   - **Pros**: Serverless, cost-effective, JSON-native
   - **Cons**: No JOINs, limited transactions, no aggregations, complex validation logic

2. **Neo4j (Graph Database)**
   - **Pros**: Natural tree operations, relationship queries, graph algorithms
   - **Cons**: Not in AWS Always Free tier, additional complexity, learning curve

3. **MongoDB (Document Database)**
   - **Pros**: JSON-native, flexible schema, horizontal scaling
   - **Cons**: Not in AWS Always Free tier, eventual consistency challenges

#### Requirements Analysis Results

| Requirement | PostgreSQL | DynamoDB | Winner |
|-------------|------------|----------|---------|
| Domain Management | 🏆 Rich JSONB queries | ⚠️ Limited validation | PostgreSQL |
| Quiz Interface | 🏆 Complex JOINs | ⚠️ Multiple queries | PostgreSQL |
| Progress Tracking | 🏆 Built-in aggregations | ⚠️ Application-level | PostgreSQL |
| Data Persistence | 🏆 ACID transactions | ⚠️ Eventually consistent | PostgreSQL |
| Answer Evaluation | 🏆 Rich analytics | ⚠️ Limited querying | PostgreSQL |
| Batch Upload | 🏆 Atomic operations | ⚠️ No batch transactions | PostgreSQL |

**Verdict**: PostgreSQL provides superior support for the system's complex relational requirements, data integrity needs, and analytical capabilities.

## Domain-Agnostic Tree Data Model

### Core Concept

The system implements a generic tree structure that separates **content** (domain-specific data) from **structure** (hierarchical relationships):

```typescript
interface TreeNode<T> {
  id: string              // Unique identifier
  parentId: string | null // Tree relationship
  children: string[]      // Child node references
  data: T                 // Domain-specific payload (JSONB)
  metadata: NodeMetadata  // Structural metadata
}
```

### Benefits

1. **Domain Agnostic**: Same tree operations work for AWS terms, Python decorators, or any future subject
2. **Flexible Schema**: JSONB data field adapts to different content types without migrations
3. **Relational Integrity**: Foreign keys maintain tree structure consistency
4. **Rich Queries**: SQL + JSONB operators enable complex operations

## Database Schema

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tree Nodes Table (Core Innovation)
```sql
CREATE TABLE tree_nodes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  parent_id UUID REFERENCES tree_nodes(id),
  user_id UUID REFERENCES users(id) NOT NULL,
  node_type VARCHAR(50) NOT NULL, -- 'domain', 'category', 'term'
  data JSONB NOT NULL,            -- Domain-specific payload
  metadata JSONB DEFAULT '{}',    -- Structural metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Quiz Sessions Table
```sql
CREATE TABLE quiz_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) NOT NULL,
  domain_id UUID REFERENCES tree_nodes(id) NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  current_term_index INTEGER DEFAULT 0,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  paused_at TIMESTAMP
);
```

#### Progress Records Table
```sql
CREATE TABLE progress_records (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) NOT NULL,
  term_id UUID REFERENCES tree_nodes(id) NOT NULL,
  session_id UUID REFERENCES quiz_sessions(id),
  student_answer TEXT NOT NULL,
  correct_answer TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL,
  similarity_score DECIMAL(3,2),
  attempt_number INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Batch Upload Records Table
```sql
CREATE TABLE batch_uploads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  admin_id UUID REFERENCES users(id) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  subject_count INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'completed',
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata JSONB DEFAULT '{}'
);
```

### Performance Indexes

```sql
-- Tree traversal optimization
CREATE INDEX idx_tree_nodes_parent ON tree_nodes(parent_id);
CREATE INDEX idx_tree_nodes_user ON tree_nodes(user_id);
CREATE INDEX idx_tree_nodes_type ON tree_nodes(node_type);

-- JSONB content search optimization
CREATE INDEX idx_tree_nodes_data_gin ON tree_nodes USING GIN (data);

-- Progress tracking optimization
CREATE INDEX idx_progress_user_term ON progress_records(user_id, term_id);
CREATE INDEX idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX idx_batch_uploads_admin ON batch_uploads(admin_id);
```

## JSONB Data Payloads

### Domain Payload
```json
{
  "name": "AWS Certification",
  "description": "Cloud services and concepts",
  "subject": "aws",
  "difficulty": "intermediate",
  "estimated_hours": 40
}
```

### Term Payload
```json
{
  "term": "Lambda",
  "definition": "Serverless compute service that runs code without provisioning servers",
  "examples": [
    "Event-driven functions",
    "API backends",
    "Data processing"
  ],
  "difficulty": "intermediate",
  "code_example": "import json\ndef lambda_handler(event, context):\n    return {'statusCode': 200}"
}
```

### Category Payload (Optional)
```json
{
  "name": "Compute Services",
  "description": "AWS services for running applications",
  "order": 1
}
```

## Query Patterns

### Domain-Agnostic Operations

#### Get All Terms in a Domain
```sql
SELECT t.data->>'term', t.data->>'definition'
FROM tree_nodes t
WHERE t.parent_id = $1 AND t.node_type = 'term'
ORDER BY t.data->>'term';
```

#### Search Across All Domains
```sql
SELECT d.data->>'name' as domain, t.data->>'term', t.data->>'definition'
FROM tree_nodes t
JOIN tree_nodes d ON d.id = t.parent_id
WHERE t.node_type = 'term'
AND (
  t.data->>'term' ILIKE $1 
  OR t.data->>'definition' ILIKE $1
)
ORDER BY d.data->>'name', t.data->>'term';
```

#### Filter by Difficulty
```sql
SELECT * FROM tree_nodes 
WHERE node_type = 'term'
AND data->>'difficulty' = 'intermediate'
AND data ? 'examples'
AND jsonb_array_length(data->'examples') > 1;
```

### Progress Analytics

#### User Progress Dashboard
```sql
WITH user_progress AS (
  SELECT 
    t.parent_id as domain_id,
    COUNT(*) as total_terms,
    COUNT(CASE WHEN pr.is_correct THEN 1 END) as mastered_terms,
    AVG(pr.similarity_score) as avg_score
  FROM tree_nodes t
  LEFT JOIN progress_records pr ON t.id = pr.term_id AND pr.user_id = $1
  WHERE t.node_type = 'term'
  GROUP BY t.parent_id
)
SELECT 
  d.data->>'name' as domain_name,
  up.mastered_terms::float / up.total_terms * 100 as completion_percentage,
  up.avg_score,
  up.total_terms,
  up.mastered_terms
FROM user_progress up
JOIN tree_nodes d ON d.id = up.domain_id
ORDER BY completion_percentage DESC;
```

#### Term Difficulty Analysis
```sql
SELECT 
  t.data->>'term',
  t.data->>'difficulty',
  COUNT(pr.id) as attempt_count,
  AVG(pr.similarity_score) as avg_similarity,
  COUNT(CASE WHEN pr.is_correct THEN 1 END)::float / COUNT(pr.id) * 100 as success_rate
FROM tree_nodes t
LEFT JOIN progress_records pr ON t.id = pr.term_id
WHERE t.node_type = 'term'
GROUP BY t.id, t.data->>'term', t.data->>'difficulty'
HAVING COUNT(pr.id) > 0
ORDER BY success_rate ASC;
```

### Quiz Logic

#### Get Next Unanswered Question
```sql
SELECT t.id, t.data->>'term', t.data->>'definition'
FROM tree_nodes t
WHERE t.parent_id = $1 -- domain_id
AND t.node_type = 'term'
AND t.id NOT IN (
  SELECT pr.term_id 
  FROM progress_records pr 
  WHERE pr.user_id = $2 AND pr.is_correct = true
)
ORDER BY RANDOM()
LIMIT 1;
```

#### Resume Quiz Session
```sql
SELECT 
  qs.*,
  d.data->>'name' as domain_name,
  COUNT(t.id) as total_terms,
  qs.current_term_index
FROM quiz_sessions qs
JOIN tree_nodes d ON d.id = qs.domain_id
JOIN tree_nodes t ON t.parent_id = qs.domain_id AND t.node_type = 'term'
WHERE qs.id = $1 AND qs.status = 'paused'
GROUP BY qs.id, d.data->>'name';
```

## Deployment Strategies

### Local Development
```yaml
Database: PostgreSQL 15 (Docker container)
Connection: Direct connection string
Environment: Full SQL access, debugging tools
Cost: Free
```

### Production Options

#### Option 1: Aurora Serverless PostgreSQL
```yaml
Database: Aurora Serverless v2 PostgreSQL
Scaling: 0 ACU to auto-scale based on demand
Cost: ~$1-5/month for light usage
Benefits: Serverless, PostgreSQL compatible, scales to zero
```

#### Option 2: RDS PostgreSQL (12-month free tier)
```yaml
Database: RDS PostgreSQL db.t3.micro
Cost: Free for 12 months, then ~$15-20/month
Benefits: Managed service, automated backups, Multi-AZ
```

## Migration Considerations

### Schema Evolution
```sql
-- Adding new content types requires no schema changes
INSERT INTO tree_nodes (node_type, data) VALUES 
('term', '{"term": "New Concept", "definition": "...", "new_field": "value"}');

-- JSONB flexibility handles new fields automatically
SELECT data FROM tree_nodes WHERE data ? 'new_field';
```

### Data Migration
```bash
# Local to Aurora Serverless
pg_dump tutor_system > local_data.sql
psql -h aurora-endpoint -U username -d tutor_system < local_data.sql
```

### Backup Strategy
```sql
-- Automated backups via RDS/Aurora
-- Point-in-time recovery available
-- Cross-region replication for disaster recovery
```

## Performance Characteristics

### Expected Performance
- **Tree traversal**: Sub-millisecond with proper indexing
- **JSONB queries**: Fast with GIN indexes
- **Progress analytics**: Efficient with aggregation queries
- **Concurrent users**: Hundreds with proper connection pooling

### Optimization Strategies
1. **Connection Pooling**: Use RDS Proxy for Lambda functions
2. **Query Optimization**: Leverage JSONB indexes for content search
3. **Caching**: Redis for frequently accessed domain data
4. **Read Replicas**: For analytics and reporting workloads

## Conclusion

PostgreSQL with JSONB provides the optimal foundation for the Know-It-All Tutor system's domain-agnostic architecture. The combination of relational integrity, flexible JSON storage, and rich query capabilities perfectly matches the system's requirements for complex tree operations, progress analytics, and content flexibility.

The data model supports seamless scaling from local development to production deployment while maintaining consistency and performance across all knowledge domains.