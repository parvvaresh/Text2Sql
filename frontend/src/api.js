const API = '/api/v1/agent'

async function fetchJson(url, options) {
  const response = await fetch(url, options)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `خطای ${response.status}`)
  return body
}

export const getModels = () => fetchJson(`${API}/models`)

export const getStats = () => fetchJson(`${API}/stats`)

export const askAgent = (query, sessionId, model) =>
  fetchJson(`${API}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId, model: model || null }),
  })
