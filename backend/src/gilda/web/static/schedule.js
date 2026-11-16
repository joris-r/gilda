(() => {
  // The Schedule's menu opens at once beside the occurrence clicked, and the Schedule shows its
  // weeks again once today changes. A Datastar action answers each click of the menu; the answer
  // of a click that is no longer the last, or of a menu closed meanwhile, is dropped here.
  const { url, association, timezone } = document.currentScript.dataset
  const menu = document.getElementById('occurrence-menu')
  const narrow = window.matchMedia('(max-width: 560px)')
  const GAP = 8
  let latest = 0
  let anchor = null

  // Beside the anchor: on its right when it fits, else on its left, above or below; inside the
  // window. On a narrow screen, the stylesheet spans the screen's width at its bottom.
  const place = () => {
    if (!menu) return
    if (narrow.matches || !anchor || !menu.matches(':popover-open')) {
      menu.style.cssText = ''
      return
    }
    // A refresh may have replaced the occurrence clicked: the menu keeps its place.
    if (!anchor.isConnected) return
    const rect = anchor.getBoundingClientRect()
    const width = document.documentElement.clientWidth
    const height = window.innerHeight
    const w = menu.offsetWidth
    const h = menu.offsetHeight
    const clamp = (value, size, room) => Math.max(GAP, Math.min(value, room - size - GAP))
    const sides = [
      { fits: rect.right + GAP + w <= width - GAP, left: rect.right + GAP, top: rect.top },
      { fits: rect.left - GAP - w >= GAP, left: rect.left - GAP - w, top: rect.top },
      { fits: rect.bottom + GAP + h <= height - GAP, left: rect.left, top: rect.bottom + GAP },
      { fits: rect.top - GAP - h >= GAP, left: rect.left, top: rect.top - GAP - h },
    ]
    const side = sides.find((candidate) => candidate.fits)
    menu.style.inset = 'auto'
    menu.style.margin = '0'
    if (side) {
      menu.style.left = `${clamp(side.left, w, width)}px`
      menu.style.top = `${clamp(side.top, h, height)}px`
    } else {
      menu.style.left = `${Math.max(GAP, (width - w) / 2)}px`
      menu.style.top = `${Math.max(GAP, (height - h) / 2)}px`
    }
  }

  if (menu) {
    new MutationObserver(place).observe(menu, { childList: true, subtree: true })
    menu.addEventListener('toggle', place)
    window.addEventListener('resize', place)
  }

  window.gildaMenu = {
    // Called by a click on an occurrence: the menu shows its title and that the rest loads.
    open(el) {
      latest += 1
      el.dataset.click = String(latest)
      anchor = el
      const loading = document.getElementById('menu-loading')
      const body = document.getElementById('occurrence-menu-body')
      if (!menu || !loading || !body) return
      const fresh = loading.content.firstElementChild.cloneNode(true)
      fresh.querySelector('.menu-title').textContent = el.dataset.title
      body.replaceWith(fresh)
      if (!menu.matches(':popover-open')) menu.showPopover()
      place()
    },
  }

  // What Datastar patches or runs for a click on an occurrence only counts for the last click,
  // while the menu is open.
  document.addEventListener('datastar-fetch', (event) => {
    const { el, type } = event.detail
    if (!(el instanceof Element) || !el.classList.contains('occ-body')) return
    if (['started', 'finished', 'error', 'retrying', 'retries-failed'].includes(type)) return
    if (el.dataset.click !== String(latest) || !menu || !menu.matches(':popover-open')) {
      event.stopImmediatePropagation()
    }
  }, true)

  // The weeks show again as they now are once today changes, or once the screen shows again
  // after being hidden then. It is fetched apart from Datastar's actions, so that a failure
  // shows no message.
  const today = () => {
    try {
      return new Intl.DateTimeFormat('en-CA', { timeZone: timezone }).format(new Date())
    } catch {
      return new Date().toISOString().slice(0, 10)
    }
  }
  const headers = association ? { 'X-Association': association } : {}
  let known = today()
  let running = false

  const refresh = async () => {
    const weeks = document.getElementById('weeks')
    if (!weeks || running) return
    const previous = known
    known = today()
    running = true
    try {
      const query = new URLSearchParams({ from: weeks.dataset.from, to: weeks.dataset.to })
      const response = await fetch(`${url}?${query}`, { headers })
      if (response.status === 401) {
        window.location.href = '/'
        return
      }
      if (response.status === 404 && !association) {
        window.location.reload()
        return
      }
      if (!response.ok) {
        known = previous
        return
      }
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html')
      const fresh = parsed.getElementById('weeks')
      const current = document.getElementById('weeks')
      if (fresh && current) current.replaceWith(document.importNode(fresh, true))
    } catch {
      known = previous
    } finally {
      running = false
    }
  }

  const check = () => {
    if (!document.hidden && today() !== known) refresh()
  }

  setInterval(check, 30000)
  document.addEventListener('visibilitychange', check)
})()
