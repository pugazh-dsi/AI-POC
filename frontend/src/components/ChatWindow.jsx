import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function ChatWindow({ messages, isStreaming = false }) {
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom when messages change or during streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md px-6">
          <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Start a Conversation</h2>
          <p className="text-gray-500">Upload a document and ask questions to get AI-powered answers with source citations.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
      {messages.map((msg, i) => {
        const isLastMessage = i === messages.length - 1
        const isCurrentlyStreaming = isStreaming && isLastMessage && msg.role === 'assistant'

        // Get sources from either old format (msg.sources) or new AI SDK format (msg.data.sources)
        const sources = msg.sources || msg.data?.sources || []

        return (
          <div
            key={msg.id || i}
            className={`flex animate-fadeIn ${
              msg.role === 'user' ? 'justify-end' :
              msg.role === 'system' ? 'justify-center' :
              'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-3 shadow-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.role === 'system'
                  ? 'bg-green-50 text-green-800 text-sm border border-green-200'
                  : 'bg-white text-gray-900 border border-gray-200'
              }`}
            >
              <div className={`text-sm leading-relaxed prose prose-sm max-w-none ${
                msg.role === 'user'
                  ? 'prose-invert prose-p:my-1 prose-headings:text-white prose-strong:text-white prose-ul:text-white prose-ol:text-white'
                  : 'prose-p:my-1 prose-headings:text-gray-900 prose-strong:text-gray-900 prose-strong:font-semibold prose-ul:text-gray-900 prose-ol:text-gray-900'
              }`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
                {/* Show cursor animation for message being streamed */}
                {isCurrentlyStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-gray-400 animate-pulse ml-1 align-middle" />
                )}
              </div>
              {sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-600 font-medium">
                    Sources: {sources.join(', ')}
                  </p>
                </div>
              )}
              {/* Token usage display */}
              {(msg.data?.usage || msg.usage) && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <div className="flex gap-4 text-xs text-gray-600">
                    <span>
                      <span className="font-medium text-blue-600">
                        {(msg.data?.usage?.prompt_tokens || msg.usage?.prompt_tokens)?.toLocaleString()}
                      </span> prompt
                    </span>
                    <span className="text-gray-400">•</span>
                    <span>
                      <span className="font-medium text-green-600">
                        {(msg.data?.usage?.completion_tokens || msg.usage?.completion_tokens)?.toLocaleString()}
                      </span> completion
                    </span>
                    <span className="text-gray-400">•</span>
                    <span>
                      <span className="font-medium text-gray-900">
                        {(msg.data?.usage?.total_tokens || msg.usage?.total_tokens)?.toLocaleString()}
                      </span> total
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  )
}
