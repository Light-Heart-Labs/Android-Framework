import { NavLink } from 'react-router-dom'
import { useMemo } from 'react'
import {
  LayoutDashboard,
  Workflow,
  Settings,
  MessageSquare,
  ExternalLink,
  Network,
  Bot
} from 'lucide-react'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/workflows', icon: Workflow, label: 'Workflows' },
  { path: '/settings', icon: Settings, label: 'Settings' },
]

// Derive external service URLs from current host
const getExternalUrl = (port) =>
  typeof window !== 'undefined'
    ? `http://${window.location.hostname}:${port}`
    : `http://localhost:${port}`

export default function Sidebar({ status }) {
  // Helper to look up service health by name fragment
  const svcStatus = (needle) =>
    status?.services?.find(s => (s.name || '').toLowerCase().includes(needle))?.status

  // Compute external links inside component so they react to status changes
  // and avoid SSR/hydration mismatch from module-scope window access
  const externalLinks = useMemo(() => [
    { key: 'webui',    url: getExternalUrl(3000), icon: MessageSquare, label: 'Chat (WebUI)',     healthy: svcStatus('webui') === 'healthy' || svcStatus('open webui') === 'healthy' || svcStatus('openwebui') === 'healthy' },
    { key: 'n8n',      url: getExternalUrl(5678), icon: Network,       label: 'n8n Workflows',    healthy: svcStatus('n8n') === 'healthy' },
    { key: 'openclaw', url: getExternalUrl(7860), icon: Bot,           label: 'OpenClaw Agents',  healthy: svcStatus('openclaw') === 'healthy' },
  ], [status?.services])

  // Service counts with degraded nuance
  const services = status?.services || []
  const onlineCount = services.filter(s => s.status === 'healthy' || s.status === 'degraded').length
  const degradedCount = services.filter(s => s.status === 'degraded').length
  const totalCount = services.length

  // VRAM bar color based on utilization
  const vramPct = status?.gpu?.vramTotal > 0
    ? (status.gpu.vramUsed / status.gpu.vramTotal) * 100
    : 0
  const vramColor = vramPct > 90 ? 'bg-red-500' : vramPct > 75 ? 'bg-yellow-500' : 'bg-indigo-500'

  // Footer status color
  const footerColor = degradedCount > 0
    ? 'text-yellow-500'
    : onlineCount === totalCount
      ? 'text-green-500'
      : totalCount > 0
        ? 'text-yellow-500'
        : 'text-zinc-500'

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[#18181b] border-r border-zinc-800 flex flex-col">
      {/* Logo */}
      <div className="px-4 pt-4 pb-3 border-b border-zinc-800">
        <pre aria-hidden="true" className="text-[7.5px] leading-[8px] text-indigo-300 opacity-90 font-mono whitespace-pre select-none">{`    ____
   / __ \\ _____ ___   ____ _ ____ ___
  / / / // ___// _ \\ / __ \`// __ \`__ \\
 / /_/ // /   /  __// /_/ // / / / / /
/_____//_/    \\___/ \\__,_//_/ /_/ /_/
    _____
   / ___/ ___   _____ _   __ ___   _____
   \\__ \\ / _ \\ / ___/| | / // _ \\ / ___/
  ___/ //  __// /    | |/ //  __// /
 /____/ \\___//_/     |___/ \\___//_/`}</pre>
        <p className="text-[8px] text-zinc-500 font-mono tracking-wider mt-1">
          LOCAL AI // SOVEREIGN INTELLIGENCE
        </p>
        <p className="text-[10px] text-zinc-500 mt-1">
          {status?.tier || 'Loading...'} • v{status?.version || '...'}
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map(({ path, icon: Icon, label }) => (
            <li key={path}>
              <NavLink
                to={path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white relative before:content-[""] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:bg-indigo-300 before:rounded-r'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                  }`
                }
              >
                <Icon size={20} />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        {/* External Links */}
        <div className="mt-6 pt-6 border-t border-zinc-800">
          <p className="px-3 text-xs font-medium text-zinc-500 uppercase mb-2">
            Quick Links
          </p>
          <ul className="space-y-1">
            {externalLinks.map(({ key, url, icon: Icon, label, healthy }) => (
              <li key={key}>
                <a
                  href={healthy ? url : undefined}
                  onClick={(e) => { if (!healthy) e.preventDefault() }}
                  target={healthy ? '_blank' : undefined}
                  rel={healthy ? 'noopener noreferrer' : undefined}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    healthy
                      ? 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                      : 'text-zinc-600 opacity-40 cursor-not-allowed'
                  }`}
                >
                  <Icon size={20} />
                  <span>{label}</span>
                  <span className={`ml-auto text-[10px] font-mono ${healthy ? 'text-zinc-500' : 'text-zinc-600'}`}>
                    {healthy ? 'OPEN' : 'OFFLINE'}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* Status Footer */}
      <div className="p-4 border-t border-zinc-800">
        <div className="flex items-center justify-between text-sm">
          <span className="text-zinc-500">Services</span>
          <span className={footerColor}>
            {degradedCount > 0
              ? `Online: ${onlineCount}/${totalCount} · ${degradedCount} degraded`
              : `Online: ${onlineCount}/${totalCount}`
            }
          </span>
        </div>
        {status?.gpu && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-zinc-500 mb-1">
              <span>VRAM</span>
              <span className="font-mono">{(status.gpu.vramUsed || 0).toFixed(1)}/{(status.gpu.vramTotal || 0).toFixed(0)} GB</span>
            </div>
            <div className="h-1.5 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${vramColor} rounded-full transition-all`}
                style={{ width: `${Math.min(vramPct, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
