(() => {
  // A selector shows the value chosen while a save runs, then the value of the save answered last,
  // or the one it opened with: the server tells which value each successful answer saved.
  const states = new WeakMap()
  const stateOf = (el) => {
    if (!states.has(el)) states.set(el, { saved: el.dataset.saved, running: 0 })
    return states.get(el)
  }
  window.gildaPreferenceSaved = (id, value) => {
    const el = document.getElementById(id)
    if (el) stateOf(el).saved = value
  }
  document.addEventListener('datastar-fetch', (event) => {
    const { el, type } = event.detail
    if (!(el instanceof HTMLSelectElement) || !el.id.startsWith('preference-')) return
    const state = stateOf(el)
    if (type === 'started') state.running += 1
    if (type === 'finished' && (state.running -= 1) === 0) {
      el.value = state.saved
      el.className = state.saved ? `preference-${state.saved}` : ''
    }
  })
})()
