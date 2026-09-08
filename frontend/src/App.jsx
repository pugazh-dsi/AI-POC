import { useState, useEffect } from 'react'
import FileUpload from './components/FileUpload'
import ChatWindow from './components/ChatWindow'
import MessageInput from './components/MessageInput'
import { getDocuments, deleteDocument } from './api'
import { useDocumentChat } from './hooks/useDocumentChat'

function App() {
  const [documents, setDocuments] = useState([])

  // Use AI SDK's useChat hook (wrapped with our custom logic)
  const { messages, append, isLoading, addSystemMessage } = useDocumentChat()

  useEffect(() => {
    getDocuments().then(setDocuments).catch(() => {})
  }, [])

  const handleUploadSuccess = (result) => {
    setDocuments((prev) => [
      ...prev.filter((d) => d.filename !== result.filename),
      { filename: result.filename, chunks: result.chunks },
    ])
    // Use addSystemMessage for instant upload notifications (non-streamed)
    addSystemMessage(
      `"${result.filename}" uploaded and indexed successfully (${result.chunks} chunks). You can now ask questions about it!`
    )
  }

  const handleDelete = async (filename) => {
    try {
      await deleteDocument(filename)
      setDocuments((prev) => prev.filter((d) => d.filename !== filename))
    } catch {
      // silently fail
    }
  }

  const handleSend = async (question) => {
    // Use AI SDK's append method for streaming responses
    append({
      role: 'user',
      content: question,
    })
  }

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-80 bg-white border-r border-gray-200 flex flex-col shadow-sm">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">DocuChat AI</h1>
              <p className="text-xs text-gray-500">Document Q&A Assistant</p>
            </div>
          </div>
        </div>

        <FileUpload onUploadSuccess={handleUploadSuccess} />

        {/* Session Statistics */}
        <div className="px-4 py-4 bg-gray-50 border-y border-gray-200">
          <h3 className="text-xs font-medium text-gray-500 mb-3">
            Session Overview
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Documents</p>
              <p className="text-2xl font-semibold text-gray-900">{documents.length}</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Messages</p>
              <p className="text-2xl font-semibold text-gray-900">{messages.filter(m => m.role === 'user').length}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <h2 className="text-xs font-medium text-gray-500 mb-3 mt-4">
            Documents ({documents.length})
          </h2>
          {documents.length === 0 ? (
            <p className="text-sm text-gray-400">No documents uploaded yet</p>
          ) : (
            <ul className="space-y-2">
              {documents.map((doc) => (
                <li
                  key={doc.filename}
                  className="flex items-center gap-3 p-3 rounded-lg bg-white text-sm group border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="w-8 h-8 bg-blue-50 rounded-md flex items-center justify-center shrink-0">
                    <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-xs text-gray-500">{doc.chunks} chunks</p>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.filename)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-red-50 text-gray-400 hover:text-red-600 transition-all shrink-0"
                    title="Delete document"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col bg-white">
        <ChatWindow messages={messages} isStreaming={isLoading} />

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            Powered by <span className="font-medium text-blue-600">OpenAI GPT-3.5</span> •
            Built with <span className="font-medium text-gray-700">React</span> &
            <span className="font-medium text-gray-700"> AI SDK</span>
          </p>
        </div>

        <MessageInput onSend={handleSend} disabled={isLoading} />
      </main>
    </div>
  )
}

export default App
