import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import RagMode from './pages/RagMode'
import ToolsMode from './pages/ToolsMode'
import PlaceholderMode from './pages/PlaceholderMode'
import SettingsPanel from './components/SettingsPanel'
import { MODES } from './modes'
import { getProviders } from './api'

/**
 * One route per capability, so every tile is a real, shareable URL:
 *   /            landing page with the three tiles
 *   /chat        RAG
 *   /tools       Tool Calling
 *   /guardrails  Guardrails     (pipeline not built yet)
 *
 * Paths live on the mode itself (modes.jsx), so adding a tile means adding one
 * registry entry. Provider settings are global, so the panel is mounted here,
 * outside the routes, and stays open across navigation.
 *
 * Exactly one provider is active at a time; it is read once here and refreshed
 * whenever the settings panel changes it, so every tile's sidebar shows the same
 * integration badge without each page fetching it again.
 */
export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeProvider, setActiveProvider] = useState(null)
  const openSettings = () => setSettingsOpen(true)

  useEffect(() => {
    getProviders()
      .then((data) => setActiveProvider(data.providers.find((p) => p.is_active && p.configured) || null))
      .catch(() => {})
  }, [])

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage onOpenSettings={openSettings} activeProvider={activeProvider} />} />
        {MODES.map((mode) => (
          <Route
            key={mode.id}
            path={mode.path}
            element={
              mode.id === 'rag' ? (
                <RagMode mode={mode} onOpenSettings={openSettings} activeProvider={activeProvider} />
              ) : mode.id === 'tools' ? (
                <ToolsMode mode={mode} onOpenSettings={openSettings} activeProvider={activeProvider} />
              ) : (
                <PlaceholderMode mode={mode} onOpenSettings={openSettings} activeProvider={activeProvider} />
              )
            }
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onActiveChange={setActiveProvider}
      />
    </>
  )
}
