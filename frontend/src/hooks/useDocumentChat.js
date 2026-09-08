import { useChat } from 'ai/react';
import { useState, useCallback } from 'react';

/**
 * Custom hook wrapping AI SDK's useChat for document Q&A functionality.
 * Handles streaming responses with source citations and upload notifications.
 */
export function useDocumentChat() {
  const [systemMessages, setSystemMessages] = useState([]);

  const chat = useChat({
    api: '/api/chat',
    onFinish: (message, { data }) => {
      // Sources are streamed as data and automatically attached to message
      // No additional processing needed - AI SDK handles this
      console.log('Message completed:', message, 'with data:', data);
    },
    onError: (error) => {
      console.error('Chat error:', error);
      // AI SDK automatically adds error message to chat
    },
  });

  /**
   * Add a system message (non-streamed, instant display)
   * Used for upload notifications and system alerts
   */
  const addSystemMessage = useCallback((content) => {
    const systemMessage = {
      id: `system-${Date.now()}`,
      role: 'system',
      content,
      createdAt: new Date(),
    };
    setSystemMessages(prev => [...prev, systemMessage]);
  }, []);

  /**
   * Clear system messages
   */
  const clearSystemMessages = useCallback(() => {
    setSystemMessages([]);
  }, []);

  /**
   * Combined messages: system messages + chat messages
   */
  const allMessages = [
    ...systemMessages,
    ...chat.messages,
  ].sort((a, b) => {
    const timeA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
    const timeB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
    return timeA - timeB;
  });

  return {
    ...chat,
    messages: allMessages,
    addSystemMessage,
    clearSystemMessages,
  };
}
