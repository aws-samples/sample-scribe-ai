-- Voice Mode Database Migration
-- Adds voice_mode and voice_session_metadata columns to interview table

-- Add voice_mode boolean column (defaults to false for existing interviews)
ALTER TABLE interview
ADD COLUMN IF NOT EXISTS voice_mode BOOLEAN DEFAULT FALSE;

-- Add voice_session_metadata JSON column for session tracking
ALTER TABLE interview
ADD COLUMN IF NOT EXISTS voice_session_metadata JSONB DEFAULT '{}'::jsonb;

-- Create index on voice_mode for efficient querying
CREATE INDEX IF NOT EXISTS idx_interview_voice_mode ON interview(voice_mode);

-- Create index on voice_session_metadata for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_interview_voice_session_metadata ON interview USING GIN(voice_session_metadata);

-- Add comment to document the voice_session_metadata structure
COMMENT ON COLUMN interview.voice_session_metadata IS 'JSON metadata for voice sessions including session IDs, connection status, audio quality metrics, and session timestamps';