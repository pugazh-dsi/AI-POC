import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import RagMode from './pages/RagMode'
import PlaceholderMode from './pages/PlaceholderMode'
import SettingsPanel from './components/SettingsPanel'
import { MODES } from './modes'

/**
 * One route per capability, so every tile is a real, shareable URL:
 *   /            landing page with the three tiles
 *   /chat        RAG
 *   /tools       Tool Calling   (pipeline not built yet)
 *   /guardrails  Guardrails     (pipeline not built yet)
 *
 * Paths live on the mode itself (modes.jsx), so adding a tile means adding one
 * registry entry. Provider settings are global, so the panel is mounted here,
 * outside the routes, and stays open across navigation.
 */
export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const openSettings = () => setSettingsOpen(true)

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage onOpenSettings={openSettings} />} />
        {MODES.map((mode) => (
          <Route
            key={mode.id}
            path={mode.path}
            element={
              mode.id === 'rag' ? (
                <RagMode mode={mode} onOpenSettings={openSettings} />
              ) : (
                <PlaceholderMode mode={mode} onOpenSettings={openSettings} />
              )
            }
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  )
}
