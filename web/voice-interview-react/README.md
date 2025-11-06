# Scribe AI Voice Interview System

## Current Status: ✅ FULLY FUNCTIONAL

**Last Updated**: January 3, 2025

### System Overview

The voice interview system enables real-time voice conversations between users and an AI interviewer for knowledge capture. The system uses AWS AppSync Events for bidirectional communication and Amazon Bedrock Nova Sonic for voice processing.

## Architecture Flow

```
React App → Flask API → Lambda Function → Nova Sonic → AppSync Events → React App
```

## Components

### 1. React Voice Interface (`/web/voice-interview-react/`)
- **Location**: Compiled to `/web/static/js/voice-interface.js`
- **Audio Capture**: 16kHz mono audio via Web Audio API
- **Audio Playback**: 24kHz audio output from Nova Sonic
- **Real-time Communication**: AppSync Events for bidirectional streaming

### 2. Flask API Routes (`/web/api.py`)
- **`POST /api/interviews/{id}/voice/start`** - Initialize voice session
- **`PUT /api/interviews/{id}/voice/end`** - End session and complete interview
- **`GET /api/cognito-token`** - Provide Cognito token for AppSync authentication

### 3. Lambda Function (`/voice/`)
- **Continuous Session**: Long-running Lambda that maintains Nova Sonic connection
- **Event Processing**: Handles audio input/output and conversation management
- **Database Integration**: Saves Q&A pairs to PostgreSQL during conversation

### 4. AWS Infrastructure (`/iac/voice.tf`)
- **AppSync Events API**: Real-time bidirectional communication
- **Cognito Authentication**: User Pool tokens for secure access
- **Lambda Function**: Containerized voice processing

## Event Flow

### Session Initialization
1. User clicks "Start Voice Chat" in React app
2. React calls `POST /api/interviews/{id}/voice/start`
3. Flask invokes Lambda with `session-start` event
4. Lambda connects to AppSync Events channel and initializes Nova Sonic
5. React receives session details and connects to AppSync Events

### Voice Conversation
1. **Audio Input**: React captures microphone → base64 encoding → AppSync Events
2. **Processing**: Lambda receives audio → forwards to Nova Sonic
3. **AI Response**: Nova Sonic generates voice + text → Lambda processes
4. **Audio Output**: Lambda sends audio chunks → AppSync Events → React playback
5. **Database Storage**: Lambda saves Q&A pairs to interview record

### Session Termination
1. User clicks "End Interview" in React app
2. React calls `PUT /api/interviews/{id}/voice/end`
3. Flask updates interview status to PROCESSING and triggers summary generation
4. React redirects to interviews list (same as text interviews)

## API Endpoints

### Voice Session Management
- **`POST /api/interviews/{id}/voice/start`**
  - Initializes voice session with Lambda
  - Returns AppSync channel and session details
  
- **`PUT /api/interviews/{id}/voice/end`**
  - Stops voice session
  - Completes interview (sets status to PROCESSING)
  - Triggers summary generation via SQS

### Authentication
- **`GET /api/cognito-token`**
  - Returns Cognito access token from Flask session
  - Used by React to authenticate with AppSync Events

## Event Types

### Client → Server (ctob)
```json
{
  "direction": "ctob",
  "event": "audioInput",
  "data": {
    "blobs": ["base64_audio_chunk1", "base64_audio_chunk2"],
    "sequence": 1
  }
}
```

### Server → Client (btoc)
```json
{
  "direction": "btoc", 
  "event": "audioOutput",
  "data": {
    "blobs": ["base64_audio_chunk1", "base64_audio_chunk2"],
    "sequence": 1
  }
}
```

### Text Events
- **`textStart`** - AI begins speaking
- **`textOutput`** - AI text content (streaming)
- **`textStop`** - AI finishes speaking
- **`ready`** - System ready for audio input
- **`end`** - Session terminated

## Audio Specifications

### Input (Browser → Nova Sonic)
- **Format**: 16kHz, 16-bit, mono LPCM
- **Encoding**: Base64
- **Batching**: Multiple chunks per transmission

### Output (Nova Sonic → Browser)
- **Format**: 24kHz, 16-bit, mono LPCM  
- **Encoding**: Base64
- **Playback**: Web Audio API with AudioWorklet

## Security

### Authentication Flow
1. User authenticates with Cognito User Pool via Flask
2. Flask stores Cognito access token in session
3. React fetches token via `/api/cognito-token`
4. React uses token to authenticate with AppSync Events

### Permissions
- **Cognito Token**: Only valid for the specific AppSync Events API
- **AppSync Events**: Configured to accept tokens from the User Pool
- **Channel Access**: User can only access their own session channels

## Database Integration

### Interview Data Storage
- **Q&A Pairs**: Stored in interview `data` JSON field during conversation
- **Session Metadata**: Voice session details in `voice_session_metadata`
- **Completion**: Same workflow as text interviews (PROCESSING → summary generation)

### Data Format
```json
{
  "data": [
    {"q": "What is your experience with...", "a": "I have worked with..."},
    {"q": "Can you describe...", "a": "The process involves..."}
  ]
}
```

## Build and Deployment

### React Component Build
```bash
cd /web/voice-interview-react
npm run build
```
Outputs to `/web/static/js/voice-interface.js`

### Lambda Deployment
```bash
cd /voice
npm run build
cd ../iac
terraform apply
```

## Key Files

### React Application
- `voice-interface/index.tsx` - Main entry point
- `voice-interface/useSpeechToSpeech/index.ts` - Core voice logic
- `voice-interface/VoiceInterface.tsx` - UI component
- `voice-interface/common/schemas.ts` - Event type definitions

### Backend
- `web/api.py` - Voice API endpoints
- `web/voice.py` - Voice interview page route
- `voice/src/agent/index.ts` - Lambda main function
- `voice/src/agent/events.ts` - Event processing logic
- `iac/voice.tf` - AWS infrastructure

## Troubleshooting

### Common Issues
1. **Audio not working**: Check microphone permissions and HTTPS
2. **Connection failed**: Verify Cognito token and AppSync configuration
3. **Session timeout**: Lambda sessions auto-resume after 2-7 minutes
4. **Database errors**: Check Lambda logs for PostgreSQL connection issues

### Debug Information
- **Lambda Logs**: CloudWatch logs show detailed conversation flow
- **Browser Console**: React component logs audio processing
- **Network Tab**: Monitor AppSync Events WebSocket connection
