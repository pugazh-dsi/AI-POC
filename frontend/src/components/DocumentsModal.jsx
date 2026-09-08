import { useEffect, useState } from 'react'
import FileUpload from './FileUpload'

/**
 * The RAG tile's document workspace, in a popup: upload a file, see the session
 * stats, browse everything in the FAISS index and remove a file.
 *
 * Everything to do with documents lives here rather than in the sidebar, which
 * keeps that column for the conversation. It renders from the documents the
 * tile already holds instead of fetching again, so the list, the stats and the
 * sidebar can never disagree.
 */
export default function DocumentsModal({
  open,
  documents = [],
  messageCount = 0,
  onClose,
  onUploadSuccess,
  onDelete,
}) {
  const [filter, setFilter] = useState('')
  const [pending, setPending] = useState('')

  // Reset the search each time it opens, so it never comes back filtered.
  useEffect(() => {
    if (open) setFilter('')
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const query = filter.trim().toLowerCase()
  const visible = query
    ? documents.filter((d) => d.filename.toLowerCase().includes(query))
    : documents
  const totalChunks = documents.reduce((n, d) => n + (d.chunks || 0), 0)

  const handleDelete = async (filename) => {
    setPending(filename)
    try {
      await onDelete(filename)
    } finally {
      setPending('')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
            <p className="text-xs text-gray-500">
              Upload, browse and remove the files behind every answer.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-all"
            title="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <FileUpload onUploadSuccess={onUploadSuccess} className="" />

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Documents</p>
              <p className="text-2xl font-semibold text-gray-900">{documents.length}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Chunks indexed</p>
              <p className="text-2xl font-semibold text-gray-900">
                {totalChunks.toLocaleString()}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Questions asked</p>
              <p className="text-2xl font-semibold text-gray-900">{messageCount}</p>
            </div>
          </div>

          {documents.length > 5 && (
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter by filename…"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-400"
            />
          )}

          {documents.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">
              Nothing indexed yet — drop a PDF, TXT or DOCX above to start asking
              questions.
            </p>
          ) : visible.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No document matches “{filter.trim()}”.
            </p>
          ) : (
            <ul className="space-y-2">
              {visible.map((doc) => (
                <li
                  key={doc.filename}
                  className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 group hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="w-9 h-9 bg-blue-50 rounded-md flex items-center justify-center shrink-0">
                    <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-xs text-gray-500">{doc.chunks} chunks</p>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.filename)}
                    disabled={pending === doc.filename}
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-50 p-2 rounded-md hover:bg-red-50 text-gray-400 hover:text-red-600 transition-all shrink-0"
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

        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <p className="text-xs text-gray-500">
            Deleting a file rebuilds the FAISS index without its vectors — answers stop
            citing it immediately.
          </p>
        </div>
      </div>
    </div>
  )
}
