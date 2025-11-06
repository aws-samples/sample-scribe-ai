import React, { useState } from 'react';
import { useSpeechToSpeech } from './useSpeechToSpeech';

interface VoiceChatClientProps {
  userId: string;
  topicName?: string;
}

export const VoiceChatClient: React.FC<VoiceChatClientProps> = ({
  userId,
  topicName = 'General Knowledge'
}) => {
  const [completionModalOpen, setCompletionModalOpen] = useState(false);
  const [endReason, setEndReason] = useState<string>('');

  const {
    messages,
    isActive,
    isLoading,
    isAssistantSpeaking,
    isMuted,
    startSession,
    closeSession,
    toggleMute,
    errorMessages,
  } = useSpeechToSpeech(userId, (reason) => {
    setEndReason(reason || 'Session ended');
    setCompletionModalOpen(true);
  });

  const handleStartSession = async () => {
    await startSession();
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Voice Interview - {topicName}</h1>

      {/* Control Panel */}
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
          {!isActive ? (
            <button
              onClick={handleStartSession}
              disabled={isLoading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: isLoading ? 'not-allowed' : 'pointer'
              }}
            >
              {isLoading ? 'Starting...' : 'Start Voice Session'}
            </button>
          ) : (
            <>
              <button
                onClick={closeSession}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                End Session
              </button>
              <button
                onClick={toggleMute}
                style={{
                  padding: '10px 20px',
                  backgroundColor: isMuted ? '#ffc107' : '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {isMuted ? 'Unmute' : 'Mute'}
              </button>
            </>
          )}
        </div>

        {/* Status Indicators */}
        <div style={{ fontSize: '14px', color: '#666' }}>
          <div>Status: {isActive ? 'Active' : 'Inactive'}</div>
          {isActive && (
            <>
              <div>Assistant Speaking: {isAssistantSpeaking ? 'Yes' : 'No'}</div>
              <div>Microphone: {isMuted ? 'Muted' : 'Active'}</div>
            </>
          )}
        </div>
      </div>

      {/* Error Messages */}
      {errorMessages.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#f8d7da', border: '1px solid #f5c6cb', borderRadius: '4px' }}>
          <h4>Errors:</h4>
          {errorMessages.map((error, index) => (
            <div key={index} style={{ color: '#721c24' }}>{error}</div>
          ))}
        </div>
      )}

      {/* Messages */}
      <div style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '15px', minHeight: '400px', backgroundColor: '#f9f9f9' }}>
        <h3>Conversation</h3>
        {messages.length === 0 ? (
          <p style={{ color: '#666', fontStyle: 'italic' }}>No messages yet. Start a session to begin the conversation.</p>
        ) : (
          <div>
            {messages.map((message, index) => (
              <div
                key={message.id || index}
                style={{
                  marginBottom: '15px',
                  padding: '10px',
                  borderRadius: '8px',
                  backgroundColor: message.role === 'user' ? '#e3f2fd' : '#f3e5f5',
                  border: `1px solid ${message.role === 'user' ? '#bbdefb' : '#e1bee7'}`
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '5px', textTransform: 'capitalize' }}>
                  {message.role}:
                </div>
                <div>{message.content}</div>
                {!message.isComplete && (
                  <div style={{ fontSize: '12px', color: '#666', fontStyle: 'italic', marginTop: '5px' }}>
                    (typing...)
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completion Modal */}
      {completionModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            maxWidth: '400px',
            textAlign: 'center'
          }}>
            <h3>Session Ended</h3>
            <p>{endReason}</p>
            <button
              onClick={() => setCompletionModalOpen(false)}
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
