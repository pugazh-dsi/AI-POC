/**
 * Brand marks for the AI providers, so the settings panel and the sidebar read
 * as an integrations list rather than four identical text rows.
 *
 * Keyed by the `icon` slug the backend puts on each PROVIDER_CATALOG entry
 * (services/providers/__init__.py) — adding a provider there means adding one
 * entry here; an unknown slug falls back to a neutral plug glyph.
 */

const ICONS = {
  // OpenAI — the interlocking knot, drawn as three rotated copies of one arc set
  openai: {
    name: 'OpenAI',
    color: '#0D0D0D',
    tile: 'bg-gray-900',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M22.28 9.82a5.98 5.98 0 0 0-.52-4.91 6.05 6.05 0 0 0-6.51-2.9A6 6 0 0 0 4.98 3.65a5.98 5.98 0 0 0-4 2.9 6.05 6.05 0 0 0 .75 7.1 5.98 5.98 0 0 0 .5 4.9 6.05 6.05 0 0 0 6.52 2.9A5.98 5.98 0 0 0 13.26 24a6.05 6.05 0 0 0 5.77-4.21 5.98 5.98 0 0 0 4-2.9 6.05 6.05 0 0 0-.75-7.07Zm-9.02 12.6a4.48 4.48 0 0 1-2.88-1.04l.14-.08 4.78-2.76a.79.79 0 0 0 .39-.68v-6.74l2.02 1.17a.07.07 0 0 1 .04.06v5.58a4.5 4.5 0 0 1-4.5 4.49ZM3.6 18.3a4.47 4.47 0 0 1-.54-3l.14.09 4.79 2.76a.77.77 0 0 0 .78 0l5.84-3.37v2.33a.08.08 0 0 1-.03.06L9.73 19.98a4.5 4.5 0 0 1-6.14-1.65ZM2.34 7.9a4.48 4.48 0 0 1 2.34-1.97v5.68a.77.77 0 0 0 .38.67l5.82 3.36-2.02 1.17a.07.07 0 0 1-.07 0L3.95 14.03A4.5 4.5 0 0 1 2.34 7.9Zm16.6 3.86-5.83-3.4L15.13 7.2a.07.07 0 0 1 .07 0l4.84 2.8a4.49 4.49 0 0 1-.68 8.1v-5.68a.79.79 0 0 0-.42-.66Zm2.01-3.02-.14-.09-4.78-2.79a.78.78 0 0 0-.79 0L9.4 9.23V6.9a.07.07 0 0 1 .03-.06l4.84-2.79a4.49 4.49 0 0 1 6.67 4.65ZM8.3 12.86l-2.02-1.16a.08.08 0 0 1-.04-.06V6.07a4.49 4.49 0 0 1 7.36-3.45l-.14.08L8.68 5.46a.79.79 0 0 0-.39.68l-.01 6.72Zm1.1-2.36 2.6-1.5 2.6 1.5v3l-2.6 1.5-2.6-1.5v-3Z" />
      </svg>
    ),
  },

  // Anthropic — the angular "A" burst
  anthropic: {
    name: 'Anthropic',
    color: '#D97757',
    tile: 'bg-[#D97757]',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M17.3 3.54h-3.67l6.7 16.92H24L17.3 3.54ZM6.7 3.54 0 20.46h3.74l1.37-3.56h7.01l1.37 3.56h3.74L10.54 3.54H6.7Zm-.37 10.22 2.29-5.94 2.3 5.94H6.32Z" />
      </svg>
    ),
  },

  // Gemini — the four-pointed spark
  gemini: {
    name: 'Google Gemini',
    color: '#4285F4',
    tile: 'bg-gradient-to-br from-blue-500 to-violet-500',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M12 1.5c0 5.8 4.7 10.5 10.5 10.5C16.7 12 12 16.7 12 22.5 12 16.7 7.3 12 1.5 12 7.3 12 12 7.3 12 1.5Z" />
      </svg>
    ),
  },

  // Azure — the chevron "A"
  azure: {
    name: 'Azure OpenAI',
    color: '#0078D4',
    tile: 'bg-[#0078D4]',
    render: (props) => (
      <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
        <path d="M9.55 3.2h6.02l-6.25 18.5-6.87-.01L9.55 3.2Zm3.03 5.35 4.6 6.9-6.9 1.32 4.2 3.9h8.34L12.58 8.55Z" />
      </svg>
    ),
  },
}

const FALLBACK = {
  name: 'Provider',
  color: '#6B7280',
  tile: 'bg-gray-500',
  render: (props) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v5m6-5v5M7 8h10v4a5 5 0 0 1-10 0V8Zm5 9v4" />
    </svg>
  ),
}

export function providerBrand(icon) {
  return ICONS[icon] || FALLBACK
}

/** The bare mark, inheriting the current text colour. */
export default function ProviderIcon({ icon, className = 'w-5 h-5' }) {
  const brand = providerBrand(icon)
  return brand.render({ className, 'aria-hidden': true })
}

/** The mark on its brand-coloured tile — used for the integration rows. */
export function ProviderBadge({ icon, size = 'md' }) {
  const brand = providerBrand(icon)
  const box = size === 'sm' ? 'w-6 h-6 rounded-md' : 'w-9 h-9 rounded-lg'
  const glyph = size === 'sm' ? 'w-3.5 h-3.5' : 'w-5 h-5'

  return (
    <span
      className={`${box} ${brand.tile} flex items-center justify-center text-white shadow-sm shrink-0`}
      title={brand.name}
    >
      {brand.render({ className: glyph, 'aria-hidden': true })}
    </span>
  )
}
