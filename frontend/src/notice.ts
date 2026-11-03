let pending: string | undefined

/** Leaves a message for the next screen, when the one that has it goes away. */
export function leaveNotice(text: string) {
  pending = text
}

/** The message left for this screen, once: it does not come back on a later visit. */
export function takeNotice(): string | undefined {
  const text = pending
  pending = undefined
  return text
}
