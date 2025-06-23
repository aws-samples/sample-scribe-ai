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

#########################################################
# scope table
#########################################################
sql 'DROP TABLE IF EXISTS scope CASCADE;
' $ADMIN

sql 'CREATE TABLE IF NOT EXISTS scope (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR
);
' $ADMIN
#########################################################

#########################################################
# topic table
#########################################################
sql 'DROP TABLE IF EXISTS topic CASCADE;
' $ADMIN

sql 'CREATE TABLE IF NOT EXISTS topic (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	scope_id UUID REFERENCES scope(id) NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR,
	areas JSONB NOT NULL
);
' $ADMIN
#########################################################

#########################################################
# interview table
#########################################################
sql 'DROP TABLE IF EXISTS interview CASCADE;
' $ADMIN

sql 'CREATE TABLE IF NOT EXISTS interview (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	topic_id UUID REFERENCES topic(id) NOT NULL,
	user_id VARCHAR,
	status VARCHAR NOT NULL,
	data JSONB,
	completed TIMESTAMP WITH TIME ZONE,
	summary VARCHAR
);
' $ADMIN
#########################################################

#########################################################
# conversation table
#########################################################
sql 'DROP TABLE IF EXISTS conversation CASCADE;
' $ADMIN

sql 'CREATE TABLE IF NOT EXISTS conversation (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	scope_id UUID REFERENCES scope(id),
	user_id VARCHAR NOT NULL,
	data JSONB,
	summary VARCHAR
);
' $ADMIN
#########################################################

echo "done"
