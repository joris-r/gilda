export const PASSWORD = 'correct horse'
const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:18025'

export function uniqueEmail(name: string) {
  return `${name.toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

/** Reads the latest link Mailpit caught for `email`, and returns its token. */
export async function latestToken(email: string, timeout = 5000): Promise<string> {
  const deadline = Date.now() + timeout
  while (true) {
    const search = await fetch(
      `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`,
    )
    const { messages } = (await search.json()) as { messages: { ID: string; Created: string }[] }
    if (messages.length > 0) {
      // Mailpit IDs are not ordered by time; Created has millisecond precision.
      const latest = messages.reduce((a, b) => (Date.parse(a.Created) > Date.parse(b.Created) ? a : b))
      const message = await fetch(`${MAILPIT_URL}/api/v1/message/${latest.ID}`)
      const { Text: text } = (await message.json()) as { Text: string }
      const match = /token=([\w-]+)/.exec(text)
      if (!match) throw new Error(`no link with a token in the email sent to ${email}`)
      return match[1]
    }
    if (Date.now() > deadline) throw new Error(`no email was sent to ${email}`)
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
}
