import type { Reply } from '../mockApi'

export const alice = { id: 'u-alice', display_name: 'Alice', email: 'alice@example.org' }

export const signedInAsAlice: Reply = { status: 200, body: alice }

export const garden = { id: 'a-garden', name: 'Jardin partagé des Lilas' }
export const repairCafe = { id: 'a-repair', name: 'Repair Café Belleville' }

export function member(
  userId: string,
  displayName: string,
  role: 'manager' | 'volunteer',
  hasAccount = true,
  emailVerified = hasAccount,
) {
  return {
    user_id: userId,
    display_name: displayName,
    email: `${displayName.toLowerCase()}@example.org`,
    has_account: hasAccount,
    email_verified: emailVerified,
    role,
  }
}
