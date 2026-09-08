import { useChat } from 'ai/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createChat,
  deleteChat as deleteChatRequest,
  getChat,
  getChats,
  renameChat as renameChatRequest,
} from '../api';

/**
 * Custom hook wrapping AI SDK's useChat for document Q&A functionality.
 * Handles streaming responses with source citations and upload notifications.
 *
 * It also owns the tile's chat history: every turn is persisted by the backend
 * (see backend/app/services/chat_history.py), so this hook can list past
 * conversations, open one back into the transcript, and keep sending new turns
 * into whichever one is open. The tiles get all of that from `send`,
 * `chats`, `chatId`, `newChat`, `openChat` and `removeChat`.
 *
 * @param {{api?: string, mode?: string, persist?: boolean}} options
 *   api    endpoint to stream from. Each tile owns its own pipeline
 *          (/api/chat, /api/tools/chat, ...) but shares this hook.
 *   mode   history bucket the conversations are filed under ('rag', 'tools').
 *   persist set false to run a tile without history (nothing is stored).
 */
export function useDocumentChat({ api = '/api/chat', mode = 'rag', persist = true } = {}) {
  const [systemMessages, setSystemMessages] = useState([]);
  const [chats, setChats] = useState([]);
  const [chatId, setChatId] = useState(null);
  const [loadingChat, setLoadingChat] = useState(false);

  // The id is read inside callbacks that were created before the state
  // updated, so keep a ref alongside it.
  const chatIdRef = useRef(null);
  const setCurrentChat = useCallback((id) => {
    chatIdRef.current = id;
    setChatId(id);
  }, []);

  const chat = useChat({
    api,
    onResponse: (response) => {
      // Fallback for a turn sent without an id: the backend opens a
      // conversation and reports which one on this header.
      const id = response.headers.get('X-Chat-Id');
      if (id && !chatIdRef.current) setCurrentChat(id);
    },
    onFinish: () => {
      // Titles and previews are derived server-side from the stored turn.
      refreshChats();
    },
    onError: (error) => {
      console.error('Chat error:', error);
      // AI SDK automatically adds error message to chat
    },
  });

  const { setMessages } = chat;

  const refreshChats = useCallback(() => {
    if (!persist) return Promise.resolve();
    return getChats(mode)
      .then((data) => setChats(data.chats || []))
      .catch(() => {});
  }, [mode, persist]);

  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

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
   * Send a question into the current conversation, opening one first if this
   * is the first turn. The id travels in the request body, so the backend
   * appends to the chat the user is actually looking at.
   */
  const send = useCallback(async (content) => {
    let id = chatIdRef.current;

    if (persist && !id) {
      try {
        const created = await createChat(mode);
        id = created.id;
        setCurrentChat(id);
        setChats((prev) => [created, ...prev]);
      } catch {
        // History unavailable — still answer the question, just unsaved.
      }
    }

    return chat.append({ role: 'user', content }, { body: { chatId: id } });
  }, [chat, mode, persist, setCurrentChat]);

  /** Start a fresh conversation. The row appears once the first turn is sent. */
  const newChat = useCallback(() => {
    setCurrentChat(null);
    setMessages([]);
    clearSystemMessages();
  }, [clearSystemMessages, setCurrentChat, setMessages]);

  /** Re-open a stored conversation and continue it. */
  const openChat = useCallback(async (id) => {
    if (id === chatIdRef.current) return;
    setLoadingChat(true);
    try {
      const data = await getChat(id);
      clearSystemMessages();
      setMessages(
        (data.messages || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          createdAt: m.createdAt ? new Date(m.createdAt) : undefined,
          // Sources/usage and tool cards render from the same fields the live
          // stream produces, so a reloaded turn looks identical to a fresh one.
          ...(m.annotations ? { annotations: m.annotations } : {}),
          ...(m.toolInvocations ? { toolInvocations: m.toolInvocations } : {}),
        }))
      );
      setCurrentChat(id);
    } catch {
      // Deleted in another tab, most likely — drop it from the list.
      refreshChats();
    } finally {
      setLoadingChat(false);
    }
  }, [clearSystemMessages, refreshChats, setCurrentChat, setMessages]);

  const removeChat = useCallback(async (id) => {
    try {
      await deleteChatRequest(id);
    } catch {
      // already gone
    }
    setChats((prev) => prev.filter((c) => c.id !== id));
    if (id === chatIdRef.current) newChat();
  }, [newChat]);

  const renameChat = useCallback(async (id, title) => {
    try {
      const updated = await renameChatRequest(id, title);
      setChats((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)));
    } catch {
      refreshChats();
    }
  }, [refreshChats]);

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
    // history
    send,
    chats,
    chatId,
    loadingChat,
    newChat,
    openChat,
    removeChat,
    renameChat,
    refreshChats,
  };
}
