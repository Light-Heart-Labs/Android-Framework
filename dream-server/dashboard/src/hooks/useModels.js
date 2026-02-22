import { useState, useEffect, useCallback } from 'react'

// Mock data for development/demo - gated behind VITE_USE_MOCK_DATA env var
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true'

function getMockModels() {
  return [
    {
      id: 'Qwen/Qwen2.5-32B-Instruct-AWQ',
      name: 'Qwen2.5 32B AWQ',
      size: '15.7 GB',
      sizeGb: 15.7,
      vramRequired: 14,
      contextLength: 32768,
      specialty: 'General',
      description: 'High-quality general purpose, recommended for most users',
      tokensPerSec: 54,
      quantization: 'AWQ',
      status: 'loaded',
      fitsVram: true,
      fitsCurrentVram: false
    },
    {
      id: 'Qwen/Qwen2.5-7B-Instruct',
      name: 'Qwen2.5 7B',
      size: '4.2 GB',
      sizeGb: 4.2,
      vramRequired: 6,
      contextLength: 32768,
      specialty: 'Fast',
      description: 'Fast general-purpose model, good for simple tasks',
      tokensPerSec: 120,
      quantization: null,
      status: 'available',
      fitsVram: true,
      fitsCurrentVram: true
    },
    {
      id: 'Qwen/Qwen2.5-32B-Instruct-AWQ',
      name: 'Qwen2.5 Coder 32B AWQ',
      size: '15.7 GB',
      sizeGb: 15.7,
      vramRequired: 14,
      contextLength: 32768,
      specialty: 'Code',
      description: 'Optimized for coding tasks and technical work',
      tokensPerSec: 54,
      quantization: 'AWQ',
      status: 'downloaded',
      fitsVram: true,
      fitsCurrentVram: false
    },
    {
      id: 'Qwen/Qwen2.5-72B-Instruct-AWQ',
      name: 'Qwen2.5 72B AWQ',
      size: '35.0 GB',
      sizeGb: 35.0,
      vramRequired: 42,
      contextLength: 32768,
      specialty: 'Quality',
      description: 'Maximum quality, requires high-end GPU',
      tokensPerSec: 28,
      quantization: 'AWQ',
      status: 'available',
      fitsVram: false,
      fitsCurrentVram: false
    }
  ]
}

const MOCK_GPU = { vramTotal: 16, vramUsed: 13.2, vramFree: 2.8 }
const MOCK_CURRENT_MODEL = 'Qwen/Qwen2.5-32B-Instruct-AWQ'

// Named export for dev-only mocking (explicit opt-in via VITE_USE_MOCK_DATA)
export { getMockModels }

export function useModels() {
  const [models, setModels] = useState(USE_MOCK_DATA ? getMockModels() : [])
  const [gpu, setGpu] = useState(USE_MOCK_DATA ? MOCK_GPU : null)
  const [currentModel, setCurrentModel] = useState(USE_MOCK_DATA ? MOCK_CURRENT_MODEL : null)
  const [loading, setLoading] = useState(USE_MOCK_DATA ? false : true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(null)

  const fetchModels = useCallback(async () => {
    // If using mock data, don't attempt API call
    if (USE_MOCK_DATA) {
      setLoading(false)
      return
    }

    try {
      const response = await fetch('/api/models')
      if (!response.ok) throw new Error('Failed to fetch models')
      const data = await response.json()
      setModels(data.models)
      setGpu(data.gpu)
      setCurrentModel(data.currentModel)
      setError(null)
    } catch (err) {
      setError(err.message)
      // No silent fallback - let error propagate to UI
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchModels()
    // Refresh every 30 seconds
    const interval = setInterval(fetchModels, 30000)
    return () => clearInterval(interval)
  }, [fetchModels])

  const downloadModel = async (modelId) => {
    setActionLoading(modelId)
    try {
      const response = await fetch(`/api/models/${encodeURIComponent(modelId)}/download`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to start download')
      await fetchModels() // Refresh
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  const loadModel = async (modelId) => {
    setActionLoading(modelId)
    try {
      const response = await fetch(`/api/models/${encodeURIComponent(modelId)}/load`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to load model')
      await fetchModels() // Refresh
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  const deleteModel = async (modelId) => {
    if (!confirm(`Delete ${modelId}? This cannot be undone.`)) return
    
    setActionLoading(modelId)
    try {
      const response = await fetch(`/api/models/${encodeURIComponent(modelId)}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete model')
      await fetchModels() // Refresh
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  return {
    models,
    gpu,
    currentModel,
    loading,
    error,
    actionLoading,
    downloadModel,
    loadModel,
    deleteModel,
    refresh: fetchModels
  }
}
