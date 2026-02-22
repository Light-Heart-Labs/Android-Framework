import { useState, useEffect } from 'react'
import {
  Workflow, FileText, Mail, MessageSquare, Calendar, ExternalLink,
  Mic, Headphones, Code, Search, Upload, Brain, AudioLines,
  Volume2, Clock, Database, Lightbulb, Send, FileJson, Save,
  CheckCircle, AlertCircle, Loader2, ChevronRight, Play, Trash2,
  ArrowRight, RefreshCw
} from 'lucide-react'

// Helper to build external service URLs from current host
const getExternalUrl = (port) =>
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:${port}`
    : `http://localhost:${port}`

// Fetch with timeout to avoid hanging requests
const fetchJson = async (url, opts = {}, ms = 8000) => {
  const c = new AbortController()
  const t = setTimeout(() => c.abort(), ms)
  try {
    return await fetch(url, { ...opts, signal: c.signal })
  } finally {
    clearTimeout(t)
  }
}

// Icon mapping
const ICONS = {
  Workflow, FileText, Mail, MessageSquare, Calendar, ExternalLink,
  Mic, Headphones, Code, Search, Upload, Brain, AudioLines,
  Volume2, Clock, Database, Lightbulb, Send, FileJson, Save,
  CheckCircle, AlertCircle
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState([])
  const [categories, setCategories] = useState({})
  const [loading, setLoading] = useState(true)
  const [n8nAvailable, setN8nAvailable] = useState(false)
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [enabling, setEnabling] = useState(null)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [confirmRemove, setConfirmRemove] = useState(null)

  useEffect(() => {
    fetchWorkflows()
  }, [])

  const fetchWorkflows = async () => {
    try {
      setError(null)
      const res = await fetchJson('/api/workflows')
      if (res.ok) {
        const data = await res.json()
        setWorkflows(data.workflows || [])
        setCategories(data.categories || {})
        setN8nAvailable(data.n8nAvailable)
      }
    } catch (e) {
      setError(e.name === 'AbortError' ? 'Request timed out' : 'Failed to load workflows')
      console.error('Failed to fetch workflows:', e)
    } finally {
      setLoading(false)
    }
  }

  const enableWorkflow = async (id) => {
    setEnabling(id)
    setError(null)
    try {
      const res = await fetchJson(`/api/workflows/${id}/enable`, { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        await fetchWorkflows()
        setSelectedWorkflow(null)
        setNotice({ type: 'info', text: 'Workflow enabled successfully.' })
      } else {
        setError(data.detail || 'Failed to enable workflow')
      }
    } catch (e) {
      setError(e.name === 'AbortError' ? 'Request timed out' : e.message)
    } finally {
      setEnabling(null)
    }
  }

  const disableWorkflow = async (id) => {
    setConfirmRemove(null)
    setEnabling(id)
    try {
      const res = await fetchJson(`/api/workflows/${id}`, { method: 'DELETE' })
      if (res.ok) {
        await fetchWorkflows()
        setNotice({ type: 'info', text: 'Workflow removed.' })
      }
    } catch (e) {
      setError(e.name === 'AbortError' ? 'Request timed out' : e.message)
    } finally {
      setEnabling(null)
    }
  }

  // Group workflows by category
  const featured = workflows.filter(w => w.featured)
  const byCategory = {}
  workflows.forEach(w => {
    if (!byCategory[w.category]) byCategory[w.category] = []
    byCategory[w.category].push(w)
  })

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={32} />
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="text-zinc-400 mt-1">
            Pre-built automations you can enable with one click.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchWorkflows}
            className="text-sm text-indigo-300 hover:text-indigo-200 flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
          <a
            href={getExternalUrl(5678)}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm flex items-center gap-2 transition-colors"
          >
            Open n8n
            <ExternalLink size={14} />
          </a>
        </div>
      </div>

      {/* n8n Status Banner */}
      {!n8nAvailable && (
        <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-3">
          <AlertCircle className="text-amber-400" size={20} />
          <div>
            <p className="text-amber-300 font-medium">n8n is not responding</p>
            <p className="text-amber-400/70 text-sm">Start the n8n service to enable workflows.</p>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mb-6 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-200 flex items-center justify-between">
          <span>{error} — <button className="underline" onClick={fetchWorkflows}>Retry</button></span>
          <button onClick={() => setError(null)} className="ml-4 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {/* In-page notice */}
      {notice && (
        <div className={`mb-6 rounded-xl border p-4 text-sm flex items-center justify-between ${
          notice.type === 'danger' ? 'border-red-500/20 bg-red-500/10 text-red-200' :
          notice.type === 'warn' ? 'border-yellow-500/20 bg-yellow-500/10 text-yellow-100' :
          'border-indigo-500/20 bg-indigo-500/10 text-indigo-100'
        }`}>
          <span>{notice.text}</span>
          <button onClick={() => setNotice(null)} className="ml-4 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {/* Confirm Remove Dialog */}
      {confirmRemove && (
        <div className="mb-6 rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-4 text-sm text-yellow-100 flex items-center justify-between">
          <span>Remove this workflow from n8n?</span>
          <div className="flex items-center gap-2 ml-4">
            <button
              onClick={() => setConfirmRemove(null)}
              className="px-3 py-1 text-xs text-zinc-300 hover:text-white bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => disableWorkflow(confirmRemove)}
              className="px-3 py-1 text-xs text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
            >
              Remove
            </button>
          </div>
        </div>
      )}

      {/* Featured Workflows */}
      {featured.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4">Featured</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {featured.map(wf => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                onEnable={() => setSelectedWorkflow(wf)}
                onDisable={() => setConfirmRemove(wf.id)}
                enabling={enabling === wf.id}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Workflows by Category */}
      {Object.entries(byCategory).map(([catId, catWorkflows]) => (
        <div key={catId} className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-1">
            {categories[catId]?.name || catId}
          </h2>
          <p className="text-zinc-500 text-sm mb-4">
            {categories[catId]?.description}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {catWorkflows.map(wf => (
              <WorkflowCardCompact
                key={wf.id}
                workflow={wf}
                onEnable={() => setSelectedWorkflow(wf)}
                onDisable={() => setConfirmRemove(wf.id)}
                enabling={enabling === wf.id}
              />
            ))}
          </div>
        </div>
      ))}

      {/* n8n Info */}
      <div className="mt-8 p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
        <h3 className="text-lg font-semibold text-white mb-2">
          Powered by n8n
        </h3>
        <p className="text-sm text-zinc-400 mb-4">
          Dream Server includes n8n, a powerful workflow automation tool. 
          The workflows above are pre-configured templates — click "Enable" to import them.
          For custom workflows, open n8n directly.
        </p>
        <a 
          href={getExternalUrl(5678)} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-sm text-indigo-400 hover:text-indigo-300"
        >
          Open n8n Dashboard →
        </a>
      </div>

      {/* Enable Modal */}
      {selectedWorkflow && (
        <WorkflowModal
          workflow={selectedWorkflow}
          onClose={() => setSelectedWorkflow(null)}
          onEnable={() => enableWorkflow(selectedWorkflow.id)}
          enabling={enabling === selectedWorkflow.id}
        />
      )}
    </div>
  )
}

function WorkflowCard({ workflow, onEnable, onDisable, enabling }) {
  const Icon = ICONS[workflow.icon] || Workflow
  const isActive = workflow.status === 'active'
  const isInstalled = workflow.installed
  const depsOk = workflow.allDependenciesMet

  return (
    <div className={`p-6 bg-zinc-900/50 border rounded-xl ${
      isActive ? 'border-green-500/30' : 'border-zinc-800'
    }`}>
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-lg ${
          isActive ? 'bg-green-500/20' : 'bg-zinc-800'
        }`}>
          <Icon size={24} className={isActive ? 'text-green-400' : 'text-indigo-400'} />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">{workflow.name}</h3>
            {isActive && (
              <span className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded-full">
                Active
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-400 mt-1">{workflow.description}</p>

          {/* Diagram Preview */}
          {workflow.diagram?.steps && (
            <div className="mt-4 flex items-center gap-2 text-xs text-zinc-500">
              {workflow.diagram.steps.map((step, i) => {
                const StepIcon = ICONS[step.icon] || ChevronRight
                return (
                  <div key={i} className="flex items-center gap-1">
                    <StepIcon size={14} />
                    <span>{step.label}</span>
                    {i < workflow.diagram.steps.length - 1 && (
                      <ArrowRight size={12} className="text-zinc-600 ml-1" />
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Dependencies */}
          {!depsOk && (
            <div className="mt-3 flex items-center gap-2 text-xs text-amber-400">
              <AlertCircle size={14} />
              Missing: {Object.entries(workflow.dependencyStatus)
                .filter(([, ok]) => !ok)
                .map(([dep]) => dep)
                .join(', ')}
            </div>
          )}
          
          <div className="flex items-center justify-between mt-4">
            {isActive ? (
              <span className="text-xs text-zinc-500">
                {workflow.executions} executions
              </span>
            ) : (
              <span className="text-xs text-zinc-500">
                Setup: {workflow.setupTime}
              </span>
            )}
            
            <div className="flex gap-2">
              {isInstalled && (
                <button
                  onClick={onDisable}
                  disabled={enabling}
                  className="p-2 rounded-lg text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  title="Remove workflow"
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button 
                onClick={onEnable}
                disabled={enabling || !depsOk}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  isActive 
                    ? 'bg-zinc-700 hover:bg-zinc-600 text-white' 
                    : depsOk
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      : 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
                }`}
              >
                {enabling && <Loader2 size={14} className="animate-spin" />}
                {isActive ? 'Configure' : isInstalled ? 'Activate' : 'Enable'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function WorkflowCardCompact({ workflow, onEnable, onDisable, enabling }) {
  const Icon = ICONS[workflow.icon] || Workflow
  const isActive = workflow.status === 'active'
  const depsOk = workflow.allDependenciesMet

  return (
    <div className={`p-4 bg-zinc-900/50 border rounded-lg ${
      isActive ? 'border-green-500/30' : 'border-zinc-800'
    }`}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${
          isActive ? 'bg-green-500/20' : 'bg-zinc-800'
        }`}>
          <Icon size={18} className={isActive ? 'text-green-400' : 'text-indigo-400'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-white truncate">{workflow.name}</h3>
            {isActive && (
              <span className="w-2 h-2 bg-green-400 rounded-full" />
            )}
          </div>
          <p className="text-xs text-zinc-500 truncate">{workflow.description}</p>
        </div>
        <button
          onClick={depsOk ? onEnable : undefined}
          disabled={enabling || !depsOk}
          className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            isActive 
              ? 'bg-zinc-700 hover:bg-zinc-600 text-white' 
              : depsOk
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                : 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
          }`}
        >
          {enabling ? <Loader2 size={12} className="animate-spin" /> : isActive ? 'Open' : 'Enable'}
        </button>
      </div>
    </div>
  )
}

function WorkflowModal({ workflow, onClose, onEnable, enabling }) {
  const Icon = ICONS[workflow.icon] || Workflow
  const depsOk = workflow.allDependenciesMet

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-lg w-full shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-indigo-500/20 rounded-lg">
              <Icon size={28} className="text-indigo-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{workflow.name}</h2>
              <p className="text-zinc-400">{workflow.description}</p>
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="p-6 border-b border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-300 mb-4">How it works</h3>
          <div className="space-y-3">
            {workflow.diagram?.steps?.map((step, i) => {
              const StepIcon = ICONS[step.icon] || ChevronRight
              return (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs text-zinc-400 font-medium">
                    {i + 1}
                  </div>
                  <StepIcon size={18} className="text-indigo-400" />
                  <span className="text-white">{step.label}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Dependencies */}
        <div className="p-6 border-b border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-300 mb-3">Required Services</h3>
          <div className="flex flex-wrap gap-2">
            {workflow.dependencies?.map(dep => {
              const ok = workflow.dependencyStatus[dep]
              return (
                <span 
                  key={dep}
                  className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                    ok 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-red-500/20 text-red-400'
                  }`}
                >
                  {ok ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
                  {dep}
                </span>
              )
            })}
          </div>
          {!depsOk && (
            <p className="text-sm text-amber-400 mt-3">
              Some services need to be enabled before you can use this workflow.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onEnable}
            disabled={enabling || !depsOk}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
              depsOk
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                : 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
            }`}
          >
            {enabling && <Loader2 size={14} className="animate-spin" />}
            <Play size={14} />
            Enable Workflow
          </button>
        </div>
      </div>
    </div>
  )
}
