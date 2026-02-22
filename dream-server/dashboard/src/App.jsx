import { Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Workflows from './pages/Workflows'
import Settings from './pages/Settings'
import Sidebar from './components/Sidebar'
import SetupWizard from './components/SetupWizard'
import { useSystemStatus } from './hooks/useSystemStatus'
import { useVersion, triggerUpdate } from './hooks/useVersion'

function App() {
  const { status, loading, error } = useSystemStatus()
  const { version, dismissUpdate } = useVersion()
  const [firstRun, setFirstRun] = useState(false)

  useEffect(() => {
    // Check if this is first run (no chat history)
    const hasVisited = localStorage.getItem('dream-dashboard-visited')
    if (!hasVisited) {
      setFirstRun(true)
    }
  }, [])

  const dismissFirstRun = () => {
    localStorage.setItem('dream-dashboard-visited', 'true')
    setFirstRun(false)
  }

  return (
    <div className="flex min-h-screen bg-[#0f0f13]">
      <Sidebar status={status} />
      
      <main className="flex-1 ml-64">
        {firstRun && (
          <SetupWizard onComplete={dismissFirstRun} />
        )}
        
        {status?.bootstrap?.active && (
          <BootstrapBanner bootstrap={status.bootstrap} />
        )}
        
        {version?.update_available && (
          <UpdateBanner version={version} onDismiss={dismissUpdate} />
        )}
        
        <Routes>
          <Route path="/" element={<Dashboard status={status} loading={loading} />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

function WelcomeBanner({ onDismiss }) {
  return (
    <div className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 border-b border-indigo-500/30 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-2">
          Welcome to your AI.
        </h1>
        <p className="text-zinc-300 mb-4">
          Everything is running on this machine. Your data never leaves your network. 
          No subscriptions. No limits.
        </p>
        <button 
          onClick={onDismiss}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
        >
          Get Started
        </button>
      </div>
    </div>
  )
}

function BootstrapBanner({ bootstrap }) {
  const formatEta = (seconds) => {
    if (!seconds || seconds <= 0) return 'calculating...'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${mins}m`
  }

  const formatBytes = (bytes) => {
    if (!bytes) return '0'
    return (bytes / 1e9).toFixed(1)
  }

  return (
    <div className="bg-gradient-to-r from-indigo-900/40 to-purple-900/40 border-b border-indigo-500/30 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-indigo-400 rounded-full animate-pulse" />
            <div>
              <h3 className="text-sm font-semibold text-white">Downloading Full Model</h3>
              <p className="text-xs text-zinc-400">
                Chat now with lightweight model • <span className="text-indigo-300">{bootstrap.model}</span> downloading
              </p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xl font-bold text-indigo-400">{bootstrap.percent?.toFixed(1) || 0}%</span>
            {bootstrap.speedMbps && (
              <p className="text-xs text-zinc-500">{bootstrap.speedMbps.toFixed(1)} MB/s</p>
            )}
          </div>
        </div>
        <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
            style={{ width: `${bootstrap.percent || 0}%` }}
          />
        </div>
        <p className="text-xs text-zinc-500 mt-2">
          ETA: {formatEta(bootstrap.eta)} • {formatBytes(bootstrap.bytesDownloaded)} / {formatBytes(bootstrap.bytesTotal)} GB
        </p>
      </div>
    </div>
  )
}

function UpdateBanner({ version, onDismiss }) {
  const [updating, setUpdating] = useState(false)
  const [updateError, setUpdateError] = useState(null)
  const [updateResult, setUpdateResult] = useState(null)

  const handleBackup = async () => {
    try {
      setUpdating(true)
      setUpdateError(null)
      const result = await triggerUpdate('backup')
      setUpdateResult(result)
    } catch (err) {
      setUpdateError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  const handleUpdate = async () => {
    if (!confirm('This will update Dream Server and restart services. Continue?')) {
      return
    }
    try {
      setUpdating(true)
      setUpdateError(null)
      const result = await triggerUpdate('update')
      setUpdateResult(result)
    } catch (err) {
      setUpdateError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="bg-gradient-to-r from-emerald-900/50 to-teal-900/50 border-b border-emerald-500/30 p-4">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-emerald-100">
              Update Available: {version.current} → {version.latest}
            </h3>
            <p className="text-sm text-emerald-200/70">
              A new version of Dream Server is available. 
              {version.changelog_url && (
                <a 
                  href={version.changelog_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="underline hover:text-emerald-100 ml-1"
                >
                  View changelog
                </a>
              )}
            </p>
            {updateError && (
              <p className="text-sm text-red-400 mt-1">Error: {updateError}</p>
            )}
            {updateResult?.output && (
              <p className="text-sm text-emerald-300 mt-1">{updateResult.output}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleBackup}
            disabled={updating}
            className="px-3 py-1.5 text-sm font-medium text-emerald-200 hover:text-white bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg transition-colors disabled:opacity-50"
          >
            {updating ? 'Working...' : 'Backup'}
          </button>
          <button
            onClick={handleUpdate}
            disabled={updating}
            className="px-3 py-1.5 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors disabled:opacity-50"
          >
            {updating ? 'Updating...' : 'Update Now'}
          </button>
          <button
            onClick={onDismiss}
            disabled={updating}
            className="p-1.5 text-emerald-400 hover:text-emerald-200 hover:bg-emerald-500/10 rounded-lg transition-colors disabled:opacity-50"
            title="Dismiss"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
