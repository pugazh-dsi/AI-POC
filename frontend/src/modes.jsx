/**
 * The three tiles of the app. Each mode is the SAME chat shell with a
 * different backend pipeline behind it — see "Three-Tile Architecture" in
 * CLAUDE.md. Accent classes are written out in full because Tailwind cannot
 * see dynamically built class names.
 */

const iconProps = {
  fill: 'none',
  viewBox: '0 0 24 24',
  stroke: 'currentColor',
  strokeWidth: 1.75,
}

export const MODES = [
  {
    id: 'rag',
    path: '/chat',
    title: 'RAG',
    tagline: 'Chat with your documents',
    description:
      'Upload a PDF, TXT or DOCX. Your question is embedded, matched against the FAISS index, and answered only from the passages that come back — with source citations.',
    status: 'live',
    endpoint: '/api/chat',
    steps: ['Upload & chunk', 'Embed → FAISS search', 'Answer with citations'],
    accent: {
      icon: 'bg-blue-600',
      iconSoft: 'bg-blue-50 text-blue-600',
      border: 'hover:border-blue-400',
      text: 'text-blue-600',
      dot: 'bg-blue-500',
    },
    Icon: (props) => (
      <svg {...iconProps} {...props}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
        />
      </svg>
    ),
  },
  {
    id: 'tools',
    path: '/tools',
    title: 'Tool Calling',
    tagline: 'The model calls a function, then explains the result',
    description:
      'The model reads your question and picks a tool. The backend runs it locally, hands the raw JSON back, and the model turns that into a readable answer — a two-pass loop you can watch step by step.',
    status: 'planned',
    endpoint: '/api/tools/chat',
    steps: ['Pass 1 → tool call', 'Execute locally', 'Pass 2 → readable text'],
    accent: {
      icon: 'bg-violet-600',
      iconSoft: 'bg-violet-50 text-violet-600',
      border: 'hover:border-violet-400',
      text: 'text-violet-600',
      dot: 'bg-violet-500',
    },
    Icon: (props) => (
      <svg {...iconProps} {...props}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
        />
      </svg>
    ),
  },
  {
    id: 'guardrails',
    path: '/guardrails',
    title: 'Guardrails',
    tagline: 'Watch the defenses block an attack',
    description:
      'Fire prompt-injection attempts at the same pipeline and see which layer catches them: input sanitization, pattern detection, or the hardened system prompt. Blocked requests never reach the model.',
    status: 'planned',
    endpoint: '/api/guardrails/chat',
    steps: ['Sanitize input', 'Detect injection', 'Hardened prompt + verdict'],
    accent: {
      icon: 'bg-green-600',
      iconSoft: 'bg-green-50 text-green-700',
      border: 'hover:border-green-400',
      text: 'text-green-700',
      dot: 'bg-green-500',
    },
    Icon: (props) => (
      <svg {...iconProps} {...props}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
        />
      </svg>
    ),
  },
]

export function getMode(id) {
  return MODES.find((m) => m.id === id)
}

export function getModeByPath(path) {
  return MODES.find((m) => m.path === path)
}
