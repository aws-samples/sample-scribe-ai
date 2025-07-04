CREATE TABLE IF NOT EXISTS scope (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR
);

CREATE TABLE IF NOT EXISTS topic (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	scope_id UUID REFERENCES scope(id) NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR,
	areas JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS interview (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	topic_id UUID REFERENCES topic(id) NOT NULL,
	user_id VARCHAR,
	status VARCHAR NOT NULL,
	data JSONB,
	completed TIMESTAMP WITH TIME ZONE,
	summary VARCHAR
);

CREATE TABLE IF NOT EXISTS conversation (
  id UUID PRIMARY KEY,
	created TIMESTAMP WITH TIME ZONE NOT NULL,
	scope_id UUID REFERENCES scope(id),
	user_id VARCHAR NOT NULL,
	data JSONB,
	summary VARCHAR
);
