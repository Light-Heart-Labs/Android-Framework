import { useState, useEffect } from 'react'

// C4 fix: Use relative URL to go through nginx proxy (works for remote access)
const API_URL = import.meta.env.VITE_API_URL || ''

export function useVersion() {
  const [version, setVersion] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const checkVersion = async () => {
      try {
        const response = await fetch(`${API_URL}/api/version`)
        if (!response.ok) {
          throw new Error('Failed to check version')
        }
        const data = await response.json()
        setVersion(data)
      } catch (err) {
        setError(err.message)
        setVersion(null)
      } finally {
        setLoading(false)
      }
    }

    checkVersion()
    
    // Check every 30 minutes
    const interval = setInterval(checkVersion, 30 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const dismissUpdate = () => {
    if (version) {
      localStorage.setItem('dismissed-update', version.latest)
      setVersion({ ...version, update_available: false })
    }
  }

  return { version, loading, error, dismissUpdate }
}

export async function triggerUpdate(action) {
  // C4 fix: Use relative URL for remote access
  const apiUrl = import.meta.env.VITE_API_URL || ''
  
  const response = await fetch(`${apiUrl}/api/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action })
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Update action failed')
  }
  
  return response.json()
}
