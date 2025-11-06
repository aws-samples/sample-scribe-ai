import { useState, useRef, useMemo, useCallback } from 'react';

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isComplete: boolean;
};

const useChatHistory = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  const addMessage = useCallback((message: Message) => {
    setMessages(prev => {
      const existingIndex = prev.findIndex(m => m.id === message.id);
      if (existingIndex >= 0) {
        // Update existing message
        const updated = [...prev];
        if (message.content) {
          updated[existingIndex] = {
            ...updated[existingIndex],
            content: updated[existingIndex].content + message.content,
            isComplete: message.isComplete
          };
        } else {
          updated[existingIndex].isComplete = message.isComplete;
        }
        return updated;
      } else {
        // Add new message
        return [...prev, message];
      }
    });
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    addMessage,
    clearMessages,
  };
};

export default useChatHistory;
