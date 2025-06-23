#!/bin/bash
set -e

function sql() {
  echo $1
  aws rds-data execute-statement \
    --resource-arn ${CLUSTER_ARN} \
    --secret-arn "$2" \
    --database ${DB_NAME} \
    --sql "$1"
  echo "____"
  echo ""
}

###############################################################
# bedrock knowledge base SCHEMA
###############################################################

# add role to db using credentials if it doesn't exist
sql "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}' LOGIN;
    END IF;
END
\$\$;" $ADMIN

# add pgvector extention
sql 'CREATE EXTENSION IF NOT EXISTS vector;' $ADMIN

# create vector SCHEMA
sql "CREATE SCHEMA IF NOT EXISTS ${SCHEMA};" $ADMIN
sql "GRANT ALL ON SCHEMA ${SCHEMA} to ${DB_USER};" $ADMIN

# use bedrock kb user to create table and index
sql "CREATE TABLE IF NOT EXISTS ${SCHEMA}.${TABLE} (
  ${PKEY} uuid PRIMARY KEY,
  ${VECTOR} vector(1536),
  ${TEXT} text,
  ${METADATA} json,
  scope_name text,
  topic_name text
  );
" $USER

# required indices
sql "CREATE INDEX IF NOT EXISTS bedrock_kb_index ON
  ${SCHEMA}.${TABLE} USING hnsw (
    ${VECTOR} vector_cosine_ops
  );
" $USER
sql "CREATE INDEX IF NOT EXISTS bedrock_kb_hybrid_index ON
  ${SCHEMA}.${TABLE} USING gin (
    (to_tsvector('simple', ${TEXT}))
  );
" $USER

###############################################################
# application SCHEMA
###############################################################

# Create scope table
sql "CREATE TABLE IF NOT EXISTS scope (
  id UUID PRIMARY KEY,
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  name VARCHAR NOT NULL,
  description VARCHAR
);" $ADMIN

# Create topic table
sql "CREATE TABLE IF NOT EXISTS topic (
  id UUID PRIMARY KEY,
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  scope_id UUID REFERENCES scope(id) NOT NULL,
  name VARCHAR NOT NULL,
  description VARCHAR,
  areas JSONB NOT NULL
);" $ADMIN

# Create interview table
sql "CREATE TABLE IF NOT EXISTS interview (
  id UUID PRIMARY KEY,
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  topic_id UUID REFERENCES topic(id) NOT NULL,
  user_id VARCHAR,
  status VARCHAR NOT NULL,
  data JSONB,
  completed TIMESTAMP WITH TIME ZONE,
  summary VARCHAR
);" $ADMIN

# Create conversation table
sql "CREATE TABLE IF NOT EXISTS conversation (
  id UUID PRIMARY KEY,
  created TIMESTAMP WITH TIME ZONE NOT NULL,
  scope_id UUID REFERENCES scope(id),
  user_id VARCHAR NOT NULL,
  data JSONB,
  summary VARCHAR
);" $ADMIN

echo "done"
