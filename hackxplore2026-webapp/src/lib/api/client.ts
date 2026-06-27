const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    let body: unknown
    try {
      body = await response.json()
    } catch {
      body = await response.text()
    }
    throw new ApiError(`API ${response.status} on ${path}`, response.status, body)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const KARLSRUHE_BBOX = '8.35,48.98,8.45,49.03'
