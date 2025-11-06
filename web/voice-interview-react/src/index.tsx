import React from 'react';
import { createRoot } from 'react-dom/client';
import { SimpleVoiceChat } from './SimpleVoiceChat';

// Initialize the voice interface when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('voice-interview-component');
  if (container) {
    const root = createRoot(container);
    
    // Get user ID from global interview data or default
    const userId = 'test-user'; // TODO: Get from auth
    
    root.render(<SimpleVoiceChat userId={userId} />);
  }
});
