# Voice Interface Component

This React.js component provides voice-based interview capabilities for Scribe AI using AWS Nova Sonic speech-to-speech AI model.

## Features

- **Web Audio API Integration**: Real-time microphone access and audio processing
- **AppSync Events Client**: Bidirectional audio streaming with AWS AppSync Events
- **Audio Level Indicators**: Real-time visual feedback for recording and playback
- **Connection Status**: Visual indicators for session, AppSync, and audio status
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Flask Integration**: Seamless integration with existing Flask templates

## Build Configuration

The component is built as a single UMD bundle that can be included in Flask templates:

```bash
# Install dependencies
npm install

# Build for production
npm run build

# Build for development with source maps
npm run build:dev

# Watch mode for development
npm run build:watch
```

## Usage in Flask Templates

### 1. Include Required Scripts

```html
<!-- React and ReactDOM from CDN -->
<script
  crossorigin
  src="https://unpkg.com/react@18/umd/react.production.min.js"
></script>
<script
  crossorigin
  src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"
></script>

<!-- Voice Interface Component -->
<script src="{{ url_for('static', filename='js/voice-interface.js') }}"></script>
```

### 2. Create Container Element

```html
<div id="voice-interview-component" data-interview-id="{{ interview.id }}">
  <!-- React component will be mounted here -->
</div>
```

### 3. Auto-mounting

The component automatically mounts when the page loads if:

- A container with ID `voice-interview-component` exists
- The interview ID is available via `data-interview-id` attribute or `window.interviewId`

### 4. Manual Mounting

```javascript
// Mount the component manually
window.VoiceInterface.mount("voice-interview-component", {
  interviewId: "interview-123",
  onStatusChange: (status, message) => {
    console.log("Status:", status, message);
  },
  onError: (error) => {
    console.error("Error:", error);
  },
  onTranscription: (text, isUser) => {
    console.log("Transcription:", text, "User:", isUser);
  },
});

// Unmount the component
window.VoiceInterface.unmount("voice-interview-component");
```

## Component Props

```typescript
interface VoiceInterfaceProps {
  interviewId: string;
  onStatusChange?: (status: string, message: string) => void;
  onError?: (error: string) => void;
  onTranscription?: (transcription: string, isUser: boolean) => void;
}
```

## Audio Configuration

The component is configured for Nova Sonic compatibility:

- **Input Audio**: 16kHz, 16-bit, mono LPCM
- **Output Audio**: 24kHz, 16-bit, mono LPCM
- **Chunk Size**: ~100ms for low latency
- **Audio Processing**: Echo cancellation, noise suppression, auto gain control

## Connection Status

The component displays three status indicators:

1. **Session**: Voice session status (inactive, initializing, active, ending, error)
2. **Connection**: AppSync Events connection (disconnected, connecting, connected, error)
3. **Audio**: Audio processing status (inactive, recording, playing, error)

## Error Handling

The component handles various error scenarios:

- **Microphone Access Denied**: Clear instructions for browser permissions
- **AppSync Connection Failures**: Automatic reconnection with exponential backoff
- **Audio Processing Errors**: Graceful degradation with user feedback
- **Session Failures**: Fallback options and error reporting

## Integration with Flask Routes

The component expects these Flask API endpoints:

```python
# Start voice session
POST /api/interviews/{id}/voice/start
Response: {
    "session_id": "session-123",
    "interview_id": "interview-123",
    "status": "active",
    "appsync_channel": "/nova-sonic-voice/user/{userId}/{sessionId}",
    "appsync_endpoint": "https://appsync-endpoint.amazonaws.com",
    "message": "Voice session started"
}

# Stop voice session
POST /api/interviews/{id}/voice/stop
Response: {
    "status": "ended",
    "message": "Voice session ended"
}

# Check session status
GET /api/interviews/{id}/voice/status
Response: {
    "status": "active|inactive|error",
    "message": "Status message"
}
```

## Development

### File Structure

```
src/voice-interface/
├── index.tsx           # Entry point and Flask integration
├── VoiceInterface.tsx  # Main React component
├── AudioProcessor.ts   # Web Audio API integration
├── AppSyncClient.ts    # AppSync Events client
├── types.ts           # TypeScript type definitions
└── README.md          # This file
```

### Testing

The component includes comprehensive error handling and logging for debugging:

```javascript
// Enable debug logging
localStorage.setItem("voice-debug", "true");

// Check component status
console.log("Voice Interface Status:", window.VoiceInterface);
```

### Browser Compatibility

- **Chrome/Edge**: Full support with Web Audio API
- **Firefox**: Full support with Web Audio API
- **Safari**: Supported with some limitations
- **Mobile**: Limited support due to Web Audio API restrictions

## Security Considerations

- **Microphone Permissions**: Component requests microphone access only when needed
- **Authentication**: Uses existing Cognito authentication for AppSync Events
- **Channel Isolation**: Each user gets isolated AppSync Events channels
- **Data Privacy**: Audio data is processed in real-time, not stored client-side
