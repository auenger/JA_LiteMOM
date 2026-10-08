const STORAGE_KEY = 'wms_login_credentials'
const REMEMBER_KEY = 'wms_remember_login'

export interface LoginCredentials {
  username: string
  password: string
}

export function readLoginCredentials(): LoginCredentials | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return null
    const value: unknown = JSON.parse(stored)
    if (typeof value !== 'object' || value === null) throw new Error('Invalid saved credentials')
    const credentials = value as Record<string, unknown>
    if (typeof credentials.username !== 'string' || typeof credentials.password !== 'string') {
      throw new Error('Invalid saved credentials')
    }
    return { username: credentials.username, password: credentials.password }
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function saveLoginCredentials(credentials: LoginCredentials) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(credentials))
}

export function clearLoginCredentials() {
  localStorage.removeItem(STORAGE_KEY)
}

export function readRememberPreference() {
  return localStorage.getItem(REMEMBER_KEY) !== 'false'
}

export function saveRememberPreference(remember: boolean) {
  localStorage.setItem(REMEMBER_KEY, String(remember))
}

export function updateSavedPassword(username: string, password: string) {
  const credentials = readLoginCredentials()
  if (credentials?.username === username) saveLoginCredentials({ username, password })
}
