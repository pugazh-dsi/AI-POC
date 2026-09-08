import { useState, useEffect } from 'react'
import ChatShell from '../components/ChatShell'
import FileUpload from '../components/FileUpload'
import { getDocuments, deleteDocument } from '../api'
import { useDocumentChat } from '../hooks/useDocumentChat'

/**
 * RAG tile: upload documents, ask questions, get answers cited back to the
 * passages the model actually saw. This is the pipeline that ships today.
 */
export default function RagMode({ mode, onOpenSettings, activeProvider }) {
  const [documents, setDocuments] = useState([])

  const { messages, append, isLoading, addSystemMessage } = useDocumentChat({
    api: mode.endpoint,
  })

  useEffect(() => {
    getDocuments().then(setDocuments).catch(() => {})
  }, [])

  const handleUploadSuccess = (result) => {
    setDocuments((prev) => [
      ...prev.filter((d) => d.filename !== result.filename),
      { filename: result.filename, chunks: result.chunks },
    ])
    // Instant, non-streamed confirmation in the transcript
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

  const handleSend = (question) => {
    append({ role: 'user', content: question })
  }

  // The active provider is reported per answer as a stream annotation, so the
  // footer reflects whatever is configured under Settings rather than a
  // hardcoded model name.
  const lastMeta = [...messages].reverse().find((m) => m.annotations?.[0])?.annotations?.[0]

  const sidebar = (
    <>
      <FileUpload onUploadSuccess={handleUploadSuccess} />

      <div className="px-4 py-4 bg-gray-50 border-y border-gray-200">
        <h3 className="text-xs font-medium text-gray-500 mb-3">Session Overview</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Documents</p>
            <p className="text-2xl font-semibold text-gray-900">{documents.length}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Messages</p>
            <p className="text-2xl font-semibold text-gray-900">
              {messages.filter((m) => m.role === 'user').length}
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 pb-4">
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
    </>
  )

  return (
    <ChatShell
      mode={mode}
      onOpenSettings={onOpenSettings}
      activeProvider={activeProvider}
      sidebar={sidebar}
      messages={messages}
      isStreaming={isLoading}
      onSend={handleSend}
      placeholder="Ask a question about your documents..."
      footer={
        lastMeta?.provider
          ? `Answered by ${lastMeta.provider} • ${lastMeta.model}`
          : 'Provider and model are configured under Settings'
      }
    />
  )
}
