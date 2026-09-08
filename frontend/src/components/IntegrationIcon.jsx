/**
 * Brand marks for the connected systems the Tool Calling tile groups its
 * catalog by.
 *
 * Keyed by the `icon` slug on each INTEGRATIONS entry
 * (services/tools/registry.py) — adding an integration there means adding one
 * entry here; an unknown slug falls back to a neutral plug glyph, so the UI
 * never breaks on a backend that is ahead of it.
 */

const ICONS = {
  // Built-in tools — a wrench, matching the tile's own icon
  core: {
    name: 'Built-in',
    tile: 'bg-gray-900',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} {...props}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085"
        />
      </svg>
    ),
  },

  // AWS — the arrow-smile under the wordmark, drawn on its own
  aws: {
    name: 'AWS',
    tile: 'bg-[#232F3E]',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M6.76 10.4c0 .3.03.54.09.71.07.18.16.37.28.58a.35.35 0 0 1 .06.18c0 .08-.05.16-.15.23l-.5.33a.38.38 0 0 1-.2.07c-.09 0-.17-.04-.25-.12a2.5 2.5 0 0 1-.3-.39 6.4 6.4 0 0 1-.26-.49c-.62.73-1.4 1.1-2.33 1.1-.67 0-1.2-.2-1.59-.57-.39-.38-.58-.89-.58-1.52 0-.67.24-1.22.72-1.63.48-.41 1.12-.62 1.94-.62.27 0 .55.02.84.06.3.05.6.11.92.19v-.58c0-.6-.13-1.02-.37-1.26-.25-.24-.68-.36-1.3-.36-.28 0-.57.04-.87.11-.3.07-.58.16-.86.27a2.3 2.3 0 0 1-.28.1.5.5 0 0 1-.13.03c-.11 0-.17-.08-.17-.25v-.4c0-.13.02-.22.06-.28a.6.6 0 0 1 .22-.17c.28-.14.61-.26 1-.36.39-.1.8-.15 1.24-.15.95 0 1.64.21 2.08.64.44.44.66 1.1.66 1.98v2.6Zm-3.22 1.2c.27 0 .55-.05.84-.15.29-.1.55-.28.77-.53.13-.15.23-.33.28-.53.05-.2.09-.44.09-.72v-.35a6.7 6.7 0 0 0-1.5-.19c-.53 0-.92.1-1.19.32-.26.2-.39.5-.39.9 0 .37.1.65.29.84.19.2.46.29.81.29Zm6.37.86c-.15 0-.25-.03-.31-.08-.07-.05-.12-.17-.17-.33L7.55 5.9a1.5 1.5 0 0 1-.08-.34c0-.14.07-.21.2-.21h.78c.16 0 .27.02.33.08.07.05.12.17.16.33l1.34 5.26 1.24-5.26c.04-.16.09-.28.15-.33.07-.06.18-.08.34-.08h.63c.16 0 .27.02.34.08.07.05.12.17.15.33l1.26 5.32 1.38-5.32c.05-.16.1-.28.17-.33.06-.06.17-.08.33-.08h.73c.14 0 .21.07.21.21a.8.8 0 0 1-.02.14 1.2 1.2 0 0 1-.06.21l-1.93 6.15c-.05.16-.1.28-.17.33-.06.05-.17.08-.31.08h-.68c-.16 0-.27-.03-.34-.09-.07-.06-.12-.17-.15-.34l-1.24-5.13-1.23 5.12c-.04.17-.09.28-.15.34-.07.06-.19.09-.34.09h-.68Zm10.2.21c-.42 0-.83-.05-1.23-.14-.4-.1-.72-.2-.92-.32a.58.58 0 0 1-.25-.23.57.57 0 0 1-.05-.22v-.42c0-.17.07-.25.19-.25.05 0 .1.01.15.03l.2.08c.27.12.57.22.88.28.32.06.64.1.96.1.5 0 .9-.09 1.17-.27.28-.18.42-.43.42-.76a.7.7 0 0 0-.2-.51c-.12-.14-.36-.27-.7-.39l-1-.31c-.51-.16-.88-.4-1.11-.71a1.66 1.66 0 0 1-.35-1.01c0-.3.06-.55.19-.78.13-.23.3-.42.5-.58.22-.16.46-.28.75-.36.28-.08.58-.12.9-.12.16 0 .32.01.49.03l.48.08c.15.04.3.07.43.12.14.04.24.09.32.13.1.06.18.12.22.19.05.06.07.15.07.26v.38c0 .17-.06.26-.19.26a.85.85 0 0 1-.31-.1 3.75 3.75 0 0 0-1.57-.32c-.46 0-.82.07-1.07.23-.25.15-.38.38-.38.71 0 .22.08.4.23.55.15.14.42.28.8.4l.98.32c.5.16.86.38 1.08.67.21.28.32.6.32.97 0 .3-.07.58-.19.82-.13.24-.3.45-.53.62-.22.17-.48.3-.79.38-.32.1-.65.14-1.02.14ZM21.7 17.7c-2.61 1.93-6.4 2.95-9.66 2.95a17.5 17.5 0 0 1-11.8-4.5c-.25-.22-.03-.52.26-.35a23.76 23.76 0 0 0 11.8 3.13c2.9 0 6.08-.6 9.01-1.84.44-.19.81.29.39.61Zm1.09-1.24c-.34-.43-2.21-.2-3.05-.1-.26.03-.3-.19-.07-.35 1.49-1.05 3.94-.75 4.23-.4.28.36-.08 2.81-1.48 3.99-.21.18-.42.09-.32-.15.32-.79 1.04-2.56.7-2.99Z" />
      </svg>
    ),
  },

  // MCP — a socket, for the tools a connected MCP server contributes. One
  // group per server, so this mark stands in for all of them.
  mcp: {
    name: 'MCP server',
    tile: 'bg-gray-800',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" {...props}>
        <path d="M3.5 15.5 12.8 6.2a2.9 2.9 0 0 1 4.1 4.1L9.6 17.6a1.45 1.45 0 0 0 2.05 2.05l6.9-6.9" />
        <path d="M7.1 19.1 3.5 15.5m3.6 3.6-1.9 1.9m1.9-1.9-1.7-1.7" />
      </svg>
    ),
  },

  // Snowflake — the six-spoke flake
  snowflake: {
    name: 'Snowflake',
    tile: 'bg-[#29B5E8]',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" {...props}>
        <path d="M12 2.5v19M3.77 6.75l16.46 10.5M20.23 6.75 3.77 17.25" />
        <path d="M12 6.2 9.9 4.1M12 6.2l2.1-2.1M12 17.8l-2.1 2.1M12 17.8l2.1 2.1" />
        <path d="m6.95 9.1-2.87-.77M6.95 9.1l-.77-2.87M17.05 14.9l2.87.77M17.05 14.9l.77 2.87" />
        <path d="m17.05 9.1 2.87-.77M17.05 9.1l.77-2.87M6.95 14.9l-2.87.77M6.95 14.9l-.77 2.87" />
      </svg>
    ),
  },

  // Google — the four-colour "G"
  google: {
    name: 'Google Workspace',
    tile: 'bg-white border border-gray-200',
    multicolor: true,
    render: (props) => (
      <svg viewBox="0 0 24 24" {...props}>
        <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47a5.53 5.53 0 0 1-2.4 3.63v3h3.86c2.26-2.09 3.56-5.17 3.56-8.87Z" />
        <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09A11.99 11.99 0 0 0 12 24Z" />
        <path fill="#FBBC05" d="M5.27 14.29A7.2 7.2 0 0 1 4.89 12c0-.8.14-1.57.38-2.29V6.62H1.29A11.86 11.86 0 0 0 0 12c0 1.94.46 3.77 1.29 5.38l3.98-3.09Z" />
        <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.7 0 3.99 2.47 1.29 6.62l3.98 3.09C6.22 6.86 8.87 4.75 12 4.75Z" />
      </svg>
    ),
  },

  // Salesforce — the three-lobed cloud
  salesforce: {
    name: 'Salesforce',
    tile: 'bg-[#00A1E0]',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M10.01 6.2a4.2 4.2 0 0 1 3.03-1.3c1.55 0 2.9.86 3.62 2.14a3.68 3.68 0 0 1 1.5-.32A3.73 3.73 0 0 1 21.9 10.4a3.73 3.73 0 0 1-3.74 3.72c-.27 0-.53-.03-.79-.08a2.7 2.7 0 0 1-2.37 1.4c-.4 0-.79-.09-1.14-.26a3.09 3.09 0 0 1-2.87 1.94c-1.2 0-2.24-.69-2.75-1.7a2.86 2.86 0 0 1-.94.16A2.9 2.9 0 0 1 4.4 12.7c0-1.06.57-1.99 1.43-2.5a3.34 3.34 0 0 1-.28-1.34A3.36 3.36 0 0 1 8.92 5.5c.4 0 .78.07 1.09.2Z" />
      </svg>
    ),
  },
}

const FALLBACK = {
  name: 'Integration',
  tile: 'bg-gray-400',
  render: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15.75 5.25v3M8.25 5.25v3M6 8.25h12v4.5a6 6 0 0 1-4.5 5.81v2.19h-3v-2.19A6 6 0 0 1 6 12.75v-4.5Z"
      />
    </svg>
  ),
}

export function getIntegrationIcon(slug) {
  return ICONS[slug] || FALLBACK
}

/**
 * `tile` draws the mark on its brand-coloured square; without it the glyph
 * inherits the surrounding text colour.
 */
export default function IntegrationIcon({ slug, className = 'w-4 h-4', tile = false }) {
  const icon = getIntegrationIcon(slug)

  if (!tile) return icon.render({ className })

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md shrink-0 ${icon.tile} ${
        icon.multicolor ? '' : 'text-white'
      }`}
      style={{ width: 28, height: 28 }}
      title={icon.name}
    >
      {icon.render({ className: 'w-4 h-4' })}
    </span>
  )
}
