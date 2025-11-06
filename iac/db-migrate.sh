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

sql "ALTER TABLE interview
ADD COLUMN IF NOT EXISTS voice_mode BOOLEAN DEFAULT FALSE;
" $ADMIN

sql "ALTER TABLE interview
ADD COLUMN IF NOT EXISTS voice_session_metadata JSONB DEFAULT '{}'::jsonb;
" $ADMIN

sql "CREATE INDEX IF NOT EXISTS idx_interview_voice_mode ON interview(voice_mode);
" $ADMIN

sql "CREATE INDEX IF NOT EXISTS idx_interview_voice_session_metadata ON interview USING GIN(voice_session_metadata);
" $ADMIN

sql "COMMENT ON COLUMN interview.voice_session_metadata IS 'JSON metadata for voice sessions including session IDs, connection status, audio quality metrics, and session timestamps';
" $ADMIN

sql "CREATE TABLE IF NOT EXISTS settings (
  key VARCHAR(255) PRIMARY KEY,
  value TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
" $ADMIN

sql "INSERT INTO settings (key, value) VALUES ('talk_mode_enabled', 'true')
ON CONFLICT (key) DO NOTHING;
" $ADMIN

sql "COMMENT ON TABLE settings IS 'System-wide configuration settings stored as key-value pairs';
" $ADMIN
