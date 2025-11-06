import React, { useState, useRef, useEffect } from 'react';
import { useSpeechToSpeech } from './useSpeechToSpeech';

interface SimpleVoiceChatProps {
  userId: string;
}

export const SimpleVoiceChat: React.FC<SimpleVoiceChatProps> = ({ userId }) => {
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
    console.log('Session ended:', reason);
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleStart = async () => {
    await startSession();
  };

  const renderMessages = () => {
    if (messages.length === 0) return null;

    return (
      <div className="border rounded p-4 bg-light mb-4" style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <div className="d-flex flex-column gap-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`d-flex ${message.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
            >
              <div
                className={`p-3 rounded-3 ${message.role === 'user' ? 'text-white' : 'bg-white text-dark'}`}
                style={{
                  maxWidth: '70%',
                  backgroundColor: message.role === 'user' ? '#4361ee' : undefined,
                  wordWrap: 'break-word'
                }}
              >
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {message.content.trim()}
                </div>
                {message.role === 'assistant' && !message.isComplete && (
                  <div className="mt-2 text-muted small fst-italic">
                    {isAssistantSpeaking ? 'Speaking...' : 'Typing...'}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
    );
  };

  const renderEmptyState = () => {
    if (messages.length > 0) return null;

    return (
      <div className="text-center py-5 text-muted">
        {!isActive && !isLoading && (
          <>
            <div className="display-1 mb-3"><i className="fas fa-microphone"></i></div>
            <p>Ready to start your voice interview</p>
          </>
        )}
        {isLoading && (
          <>
            <div className="mb-3">
              <div className="spinner-border spinner-color" role="status" style={{ width: '48px', height: '48px' }}></div>
            </div>
            <p>Initializing voice interview...</p>
          </>
        )}
        {isActive && !isLoading && (
          <>
            <div className="display-1 mb-3"><i className="fas fa-microphone"></i></div>
            <p>Say hello to start the conversation!</p>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="container" style={{ maxWidth: '800px' }}>
      {/* Header */}
      <div className="text-center mb-4 pb-3 border-bottom">
        {isActive && (
          <div className="d-inline-flex align-items-center gap-2 px-3 py-2 bg-success bg-opacity-10 text-success rounded-pill small fw-medium">
            <div style={{
              width: '8px',
              height: '8px',
              backgroundColor: '#28a745',
              borderRadius: '50%',
              animation: 'pulse 2s infinite'
            }} />
            Voice Interview Active
          </div>
        )}
      </div>

      {/* Messages Area */}
      {renderMessages()}
      {renderEmptyState()}

      {/* Status Indicator */}
      {isActive && (
        <div className={`text-center mb-3 p-3 rounded ${isAssistantSpeaking ? 'bg-warning bg-opacity-25 text-warning-emphasis' : 'bg-info bg-opacity-25 text-info-emphasis'}`}>
          {isAssistantSpeaking ? '🗣️ Scribe AI is speaking...' : <><i className="fas fa-microphone"></i> Listening...</>}
        </div>
      )}

      {/* Controls */}
      <div className="d-flex justify-content-center gap-3 mb-3">
        {!isActive ? (
          <button
            onClick={handleStart}
            disabled={isLoading}
            className={`btn ${isLoading ? 'btn-secondary' : 'btn-primary'}`}
          >
            {isLoading ? 'Starting...' : 'Start Voice Interview'}
          </button>
        ) : (
          <>
            <button
              onClick={toggleMute}
              className={`btn ${isMuted ? 'btn-secondary' : 'btn-success'} d-flex align-items-center gap-2`}
            >
              {isMuted ? <i className="fas fa-microphone-slash"></i> : <i className="fas fa-microphone"></i>} {isMuted ? 'Unmute' : 'Mute'}
            </button>
            <button
              onClick={closeSession}
              className="btn btn-danger"
            >
              End Interview
            </button>
          </>
        )}
      </div>

      {/* Error Messages */}
      {errorMessages.length > 0 && (
        <div className="alert alert-danger mt-3">
          <strong>⚠️ Errors:</strong>
          {errorMessages.map((error, index) => (
            <div key={index} className="mt-1">{error}</div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};
