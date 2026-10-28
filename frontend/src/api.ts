export interface HealthStatus {
  api: 'ok'
  database: 'ok' | 'unreachable'
}

/** Resolves to undefined when the API does not answer. */
export async function getHealth(): Promise<HealthStatus | undefined> {
  try {
    const response = await fetch('/api/health')
    return (await response.json()) as HealthStatus
  } catch {
    return undefined
  }
}
