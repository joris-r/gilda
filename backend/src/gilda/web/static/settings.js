(() => {
  // Members' preferences shows again as it now is when the screen shows again after being hidden,
  // once no save of a member's selector runs. It is fetched apart from Datastar's actions, so that
  // a failure shows no message.
  const { url, association } = document.currentScript.dataset
  let running = 0
  let started = 0
  let hidden = false
  let waiting = false

  const refresh = async () => {
    waiting = false
    const before = started
    let response
    try {
      response = await fetch(url, { headers: { 'X-Association': association } })
    } catch {
      return
    }
    if (response.status === 401) {
      window.location.href = '/'
      return
    }
    if (!response.ok) return
    const text = await response.text()
    // A save began meanwhile: what was fetched may be older than it, so fetch again once it ends.
    if (running > 0 || started !== before) {
      waiting = true
      if (running === 0) refresh()
      return
    }
    const grid = document.getElementById('members-preferences')
    if (!grid) return
    const parsed = new DOMParser().parseFromString(text, 'text/html')
    const fresh = parsed.getElementById('members-preferences')
    if (fresh) grid.replaceWith(document.importNode(fresh, true))
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      hidden = true
      return
    }
    if (!hidden) return
    hidden = false
    if (running > 0) waiting = true
    else refresh()
  })

  document.addEventListener('datastar-fetch', (event) => {
    const { el, type } = event.detail
    if (!(el instanceof HTMLSelectElement) || !el.id.startsWith('member-preference-')) return
    if (type === 'started') {
      running += 1
      started += 1
    }
    if (type === 'finished') {
      running -= 1
      if (running === 0 && waiting) refresh()
    }
  })
})()
