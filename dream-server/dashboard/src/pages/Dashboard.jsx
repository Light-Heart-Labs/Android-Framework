import {
  MessageSquare,
  Mic,
  FileText,
  Workflow,
  Bot,
  Activity,
  Cpu,
  HardDrive,
  Thermometer,
  Zap,
  Shield,
  Power
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { FeatureDiscoveryBanner, FeatureProgress, FeatureGrid } from '../components/FeatureDiscovery'
import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react'

// Helper to build external service URLs from current host
const getExternalUrl = (port) =>
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:${port}`
    : `http://localhost:${port}`

// Compute overall health from services
function computeHealth(services) {
  if (!services?.length) return { text: 'Waiting for telemetry...', color: 'text-zinc-400' }
  const hasDown = services.some(s => s.status === 'down' || s.status === 'unhealthy')
  const hasDegraded = services.some(s => s.status === 'degraded')
  if (hasDown) return { text: 'Degraded — some services down.', color: 'text-red-400' }
  if (hasDegraded) return { text: 'Degraded — check services below.', color: 'text-yellow-400' }
  return { text: 'All systems nominal.', color: 'text-green-400' }
}

// Sort services: down/unhealthy first, then degraded, then healthy
const severityOrder = { down: 0, unhealthy: 1, degraded: 2, unknown: 3, healthy: 4 }
function sortBySeverity(services) {
  return [...(services || [])].sort((a, b) =>
    (severityOrder[a.status] ?? 9) - (severityOrder[b.status] ?? 9)
  )
}

export default function Dashboard({ status, loading }) {
  if (loading) {
    return (
      <div className="p-8 animate-pulse">
        <div className="h-8 bg-zinc-800 rounded w-1/3 mb-4" />
        <p className="text-sm text-zinc-500 mb-8">Linking modules... reading telemetry...</p>
        <div className="grid grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-40 bg-zinc-800 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  const health = computeHealth(status?.services)
  const servicesSorted = sortBySeverity(status?.services)

  return (
    <div className="p-8">
      {/* Header with live meta strip */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className={`mt-1 ${health.color}`}>
            {health.text}
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-500 font-mono bg-zinc-900/50 border border-zinc-800 rounded-lg px-3 py-2">
          {status?.tier && <span className="text-indigo-300">{status.tier}</span>}
          {status?.model?.name && <span>{status.model.name}</span>}
          {status?.version && <span>v{status.version}</span>}
        </div>
      </div>

      {/* Feature Discovery Banner */}
      <FeatureDiscoveryBanner />

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <FeatureCard
          icon={MessageSquare}
          title="Chat"
          description="Talk to your AI"
          href={getExternalUrl(3000)}
          status="ready"
        />
        <FeatureCard
          icon={Mic}
          title="Voice"
          description="Speak to your AI"
          href="#"
          status="coming"
        />
        <FeatureCard
          icon={FileText}
          title="Documents"
          description="Upload & ask about your files"
          href={getExternalUrl(3000)}
          status={status?.services?.find(s => s.name?.includes('Qdrant'))?.status === 'healthy' ? 'ready' : 'disabled'}
          hint="Enable profile: rag"
        />
        <FeatureCard
          icon={Workflow}
          title="Workflows"
          description="Automate anything"
          href="/workflows"
          status={status?.services?.find(s => s.name?.toLowerCase().includes('n8n') || s.name?.toLowerCase().includes('workflow'))?.status === 'healthy' ? 'ready' : 'disabled'}
          hint="Enable profile: workflows"
        />
        <FeatureCard
          icon={Bot}
          title="Agents"
          description="OpenClaw multi-agent"
          href={getExternalUrl(7860)}
          status={status?.services?.find(s => s.name?.toLowerCase().includes('openclaw'))?.status === 'healthy' ? 'ready' : 'disabled'}
          hint="Enable profile: openclaw"
        />
        <FeatureCard
          icon={Shield}
          title="Privacy Shield"
          description="PII protection for APIs"
          href="/settings"
          status={status?.services?.find(s => s.name?.toLowerCase().includes('privacy'))?.status === 'healthy' ? 'ready' : 'disabled'}
          hint="Enable profile: privacy"
        />
      </div>

      {/* System Status */}
      <h2 className="text-lg font-semibold text-white mb-4">System Status</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        {status?.gpu && (
          <>
            <MetricCard
              icon={Cpu}
              label="GPU"
              value={status.gpu.name.replace('NVIDIA ', '')}
              subvalue={`${status.gpu.utilization}% utilized`}
            />
            <MetricCard
              icon={HardDrive}
              label="VRAM"
              value={`${status.gpu.vramUsed.toFixed(1)} GB`}
              subvalue={`of ${status.gpu.vramTotal} GB`}
              percent={(status.gpu.vramUsed / status.gpu.vramTotal) * 100}
            />
            <MetricCard
              icon={Thermometer}
              label="Temperature"
              value={`${status.gpu.temperature}°C`}
              subvalue={status.gpu.temperature < 70 ? 'Normal' : 'High'}
              alert={status.gpu.temperature >= 80}
            />
            <MetricCard
              icon={Zap}
              label="Speed"
              value={`${status.model?.tokensPerSecond || 0} tok/s`}
              subvalue={status.model?.name || 'No model'}
            />
          </>
        )}
      </div>

      {/* GPU Power (if available) */}
      {status?.gpu?.powerDrawW != null && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard
            icon={Power}
            label="Power Draw"
            value={`${status.gpu.powerDrawW}W`}
            subvalue={status.gpu.powerLimitW ? `of ${status.gpu.powerLimitW}W limit` : 'live'}
            percent={status.gpu.powerLimitW ? (status.gpu.powerDrawW / status.gpu.powerLimitW) * 100 : undefined}
          />
        </div>
      )}

      {/* GPU Telemetry Waveform */}
      {status?.gpu && (
        <GpuWaveform gpu={status.gpu} />
      )}

      {/* Services Grid — sorted by severity */}
      <h2 className="text-lg font-semibold text-white mb-4">Services</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {servicesSorted.map(service => (
          <ServiceCard key={service.name} service={service} />
        ))}
      </div>

      {/* Feature Progress + Discovery */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <FeatureProgress />
        </div>
        <div className="lg:col-span-2">
          <DiscoverMoreSection />
        </div>
      </div>
    </div>
  )
}

// Mini GPU utilization waveform — 60-second window, 1s samples
function GpuWaveform({ gpu }) {
  const [samples, setSamples] = useState([])
  const maxSamples = 60

  useEffect(() => {
    setSamples(prev => {
      const next = [...prev, gpu.utilization ?? 0]
      return next.length > maxSamples ? next.slice(-maxSamples) : next
    })
  }, [gpu.utilization])

  if (samples.length < 2) return null

  const width = 600
  const height = 40
  const points = samples.map((v, i) => {
    const x = (i / (maxSamples - 1)) * width
    const y = height - (v / 100) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <div className="mb-8 p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-zinc-500 font-mono">GPU utilization</span>
        <span className="text-xs text-zinc-500 font-mono">{gpu.utilization}%</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-10" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke="rgb(99, 102, 241)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <polyline
          points={`0,${height} ${points} ${width},${height}`}
          fill="url(#waveGrad)"
          stroke="none"
        />
        <defs>
          <linearGradient id="waveGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(99, 102, 241)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="rgb(99, 102, 241)" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  )
}

function DiscoverMoreSection() {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Sparkles size={18} className="text-indigo-400" />
          <div className="text-left">
            <h3 className="text-sm font-semibold text-white">Discover More Features</h3>
            <p className="text-xs text-zinc-500">See what else your hardware can run</p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp size={18} className="text-zinc-400" />
        ) : (
          <ChevronDown size={18} className="text-zinc-400" />
        )}
      </button>

      {expanded && (
        <div className="p-4 border-t border-zinc-800">
          <FeatureGrid />
        </div>
      )}
    </div>
  )
}

function FeatureCard({ icon: Icon, title, description, href, status, hint }) {
  const isExternal = href?.startsWith('http')
  const statusColors = {
    ready: 'border-indigo-500/20 hover:border-indigo-500/35',
    disabled: 'border-zinc-700 opacity-60',
    coming: 'border-zinc-700 opacity-40'
  }

  const content = (
    <div className={`p-6 rounded-xl border-2 ${statusColors[status]} bg-zinc-900/50 transition-all cursor-pointer hover:bg-zinc-800/50`}>
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-zinc-800 rounded-lg">
          <Icon size={24} className="text-indigo-400" />
        </div>
        {status === 'ready' && (
          <span className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded-full">
            Ready
          </span>
        )}
        {status === 'coming' && (
          <span className="px-2 py-1 text-xs bg-zinc-700 text-zinc-400 rounded-full">
            Coming
          </span>
        )}
      </div>
      <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-zinc-400">{description}</p>
      {status === 'disabled' && hint && (
        <p className="text-xs text-zinc-500 mt-3 font-mono">{hint}</p>
      )}
    </div>
  )

  if (status === 'disabled' || status === 'coming') {
    return content
  }

  if (isExternal) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {content}
      </a>
    )
  }

  return <Link to={href}>{content}</Link>
}

function MetricCard({ icon: Icon, label, value, subvalue, percent, alert }) {
  return (
    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
      <div className="flex items-center gap-3 mb-2">
        <Icon size={18} className={alert ? 'text-red-400' : 'text-zinc-400'} />
        <span className="text-sm text-zinc-400">{label}</span>
      </div>
      <div className="text-xl font-semibold text-white font-mono">{value}</div>
      <div className="text-xs text-zinc-500 mt-1">{subvalue}</div>
      {percent !== undefined && (
        <div className="h-1 bg-zinc-700 rounded-full mt-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${percent > 90 ? 'bg-red-500' : percent > 70 ? 'bg-yellow-500' : 'bg-indigo-500'}`}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}

function ServiceCard({ service }) {
  const statusColors = {
    healthy: 'bg-green-500',
    degraded: 'bg-yellow-500',
    unhealthy: 'bg-red-500',
    down: 'bg-red-500',
    unknown: 'bg-zinc-500'
  }

  const formatUptime = (seconds) => {
    if (!seconds) return '—'
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }

  return (
    <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-2 h-2 rounded-full ${statusColors[service.status] || 'bg-zinc-500'}`} />
        <span className="text-sm font-medium text-white">{service.name}</span>
      </div>
      <div className="text-xs text-zinc-500 font-mono">
        :{service.port} · {formatUptime(service.uptime)}
      </div>
    </div>
  )
}

// BootstrapBanner moved to App.jsx for app-wide visibility
