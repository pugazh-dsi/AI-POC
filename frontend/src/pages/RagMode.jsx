import { useState, useEffect } from 'react'
import ChatShell from '../components/ChatShell'
import ChatHistory from '../components/ChatHistory'
import DocumentsModal from '../components/DocumentsModal'
import { getDocuments, deleteDocument } from '../api'
import { useDocumentChat } from '../hooks/useDocumentChat'

/**
 * RAG tile: upload documents, ask questions, get answers cited back to the
 * passages the model actually saw. This is the pipeline that ships today.
 *
 * Every turn is stored under the 'rag' history bucket, so the sidebar can
 * re-open an earlier conversation and carry on in it.
 *
 * Everything about documents — uploading, the stats, the full list, deleting —
 * lives in DocumentsModal behind the sidebar button, leaving that column for
 * the conversation itself.
 */
export default function RagMode({ mode, onOpenSettings, activeProvider }) {
  const [documents, setDocuments] = useState([])
  const [docsOpen, setDocsOpen] = useState(false)

  const {
    messages, isLoading, addSystemMessage,
    send, chats, chatId, newChat, openChat, removeChat, renameChat,
  } = useDocumentChat({ api: mode.endpoint, mode: mode.id })

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
    send(question)
  }

  // The active provider is reported per answer as a stream annotation, so the
  // footer reflects whatever is configured under Settings rather than a
  // hardcoded model name.
  const lastMeta = [...messages].reverse().find((m) => m.annotations?.[0])?.annotations?.[0]

  // Newest uploads land at the end of the list, so the sidebar previews the
  // last few and the popup carries the rest.
  const SIDEBAR_DOCS = 3
  const recentDocuments = [...documents].reverse().slice(0, SIDEBAR_DOCS)

  const history = (
    <ChatHistory
      chats={chats}
      chatId={chatId}
      accent={mode.accent}
      onNew={newChat}
      onOpen={openChat}
      onRename={renameChat}
      onDelete={removeChat}
    />
  )

  // Pinned to the bottom of the sidebar so it stays reachable however long the
  // chat history grows. It is the one way into everything document-related:
  // upload, stats, the full index and delete all live in the popup.
  const sidebarFooter = (
    <button
      type="button"
      onClick={() => setDocsOpen(true)}
      className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:border-gray-300 hover:bg-gray-50"
    >
      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
      </svg>
      {documents.length === 0
        ? 'Upload a document'
        : `View all documents (${documents.length})`}
    </button>
  )

  const sidebar = (
    <>
      <div className="px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-medium text-gray-500">
            Documents ({documents.length})
          </h2>
          {recentDocuments.length < documents.length && (
            <span className="text-[11px] text-gray-400">
              showing {recentDocuments.length}
            </span>
          )}
        </div>
        {documents.length === 0 ? (
          <p className="text-sm text-gray-400">
            No documents yet — upload one from the popup below.
          </p>
        ) : (
          <ul className="space-y-2">
            {recentDocuments.map((doc) => (
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
    <>
      <ChatShell
        mode={mode}
        onOpenSettings={onOpenSettings}
        activeProvider={activeProvider}
        history={history}
        sidebar={sidebar}
        sidebarFooter={sidebarFooter}
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

      <DocumentsModal
        open={docsOpen}
        documents={documents}
        messageCount={messages.filter((m) => m.role === 'user').length}
        onClose={() => setDocsOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        onDelete={handleDelete}
      />
    </>
  )
}
