#!/bin/bash
aws bedrock-agent start-ingestion-job \
	--knowledge-base-id $(terraform output -raw bedrock_knowledge_base_id) \
	--data-source-id $(terraform output -raw bedrock_knowledge_base_data_source_id)
