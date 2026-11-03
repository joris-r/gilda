import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { control, hasControl, item, mockApi, press } from '../mockApi'
import { garden, member, repairCafe, signedInAsAlice } from './fixtures'
import { planningApi, type Registration } from './planningFake'

const atelier = { id: 'a-atelier', name: 'Atelier vélo' }

function registration(
  id: string,
  status: Registration['status'],
  date: string,
  start = '10:00',
  end = '13:00',
): Registration {
  return { id, user_id: 'u-alice', display_name: 'Alice', status, date, start, end }
}

function period(first: string, last: string, registrations: number) {
  return { first, last, registrations }
}

function summary(
  association: { id: string; name: string },
  upcoming: Registration[] = [],
  planningPeriod: ReturnType<typeof period> | null = null,
  role = 'volunteer',
  obsolete: Registration[] = [],
) {
  return { ...association, role, upcoming, obsolete, planning_period: planningPeriod }
}

/** The drawing of My associations. */
const drawing = [
  summary(
    garden,
    [
      registration('r-5', 'confirmed', '2026-11-05'),
      registration('r-14', 'proposed', '2026-11-14'),
    ],
    period('2026-11-02', '2026-11-25', 2),
    'manager',
    [registration('r-12', 'confirmed', '2026-11-12')],
  ),
  summary(repairCafe, [], period('2026-11-02', '2026-11-25', 0)),
  summary(atelier),
]

/** The innermost list item mentioning `text`: a registration's line within its association. */
function line(wrapper: Parameters<typeof item>[0], text: string) {
  const element = wrapper
    .findAll('li')
    .filter((li) => li.text().includes(text))
    .at(-1)
  if (element === undefined) throw new Error(`No list item mentioning "${text}"`)
  return element
}

function mountHome(associations: ReturnType<typeof summary>[]) {
  const calls = mockApi({
    'GET /api/session': signedInAsAlice,
    'GET /api/associations': { status: 200, body: associations },
  })
  return { calls, mounting: mountApp('/') }
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  // Wednesday 4 November 2026, 10:00 in Paris.
  vi.setSystemTime(new Date('2026-11-04T09:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('My associations', () => {
  describe('summary', () => {
    it('lists the upcoming registrations of each association', async () => {
      const wrapper = await mountHome(drawing).mounting

      const text = pageText(item(wrapper, garden.name))
      expect(text).toContain('Thu 5 Nov, 10:00–13:00')
      expect(text).toContain('Sat 14 Nov, 10:00–13:00 ?')
      expect(text.indexOf('Thu 5 Nov')).toBeLessThan(text.indexOf('Sat 14 Nov'))
    })

    it('a confirmed registration is not marked "?" and has no "Confirm"', async () => {
      const wrapper = await mountHome([
        summary(garden, [registration('r-5', 'confirmed', '2026-11-05')]),
      ]).mounting

      const shown = line(wrapper, 'Thu 5 Nov')
      expect(pageText(shown)).not.toContain('?')
      expect(hasControl(shown, 'Confirm')).toBe(false)
    })

    it('a proposed registration is marked "?" and has "Confirm"', async () => {
      const wrapper = await mountHome(drawing).mounting

      expect(hasControl(line(wrapper, 'Sat 14 Nov'), 'Confirm')).toBe(true)
      expect(hasControl(line(wrapper, 'Thu 5 Nov'), 'Confirm')).toBe(false)
    })

    it('"Confirm" confirms the registration, and the summary shows it updated', async () => {
      let status: Registration['status'] = 'proposed'
      const calls = mockApi({
        'GET /api/session': signedInAsAlice,
        'GET /api/associations': () => ({
          status: 200,
          body: [summary(garden, [registration('r-14', status, '2026-11-14')])],
        }),
        [`PATCH /api/associations/${garden.id}/registrations/r-14`]: (body) => {
          status = (body as { status: Registration['status'] }).status
          return { status: 200, body: registration('r-14', status, '2026-11-14') }
        },
      })
      const wrapper = await mountApp('/')

      await press(line(wrapper, 'Sat 14 Nov'), 'Confirm')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `/api/associations/${garden.id}/registrations/r-14`,
        body: { status: 'confirmed' },
      })
      const shown = line(wrapper, 'Sat 14 Nov')
      expect(pageText(shown)).not.toContain('?')
      expect(hasControl(shown, 'Confirm')).toBe(false)
    })

    it('says "No upcoming registration." when there is none', async () => {
      const wrapper = await mountHome(drawing).mounting

      expect(pageText(item(wrapper, atelier.name))).toContain('No upcoming registration.')
      expect(pageText(item(wrapper, garden.name))).not.toContain('No upcoming registration.')
    })
  })

  describe('obsolete registrations', () => {
    it('come first, each saying "this slot no longer takes place." with "OK"', async () => {
      const wrapper = await mountHome(drawing).mounting

      const text = pageText(item(wrapper, garden.name))
      expect(pageText(line(wrapper, 'Thu 12 Nov'))).toContain(
        'Thu 12 Nov, 10:00–13:00: this slot no longer takes place.',
      )
      expect(hasControl(line(wrapper, 'Thu 12 Nov'), 'OK')).toBe(true)
      expect(text.indexOf('Thu 12 Nov')).toBeLessThan(text.indexOf('Thu 5 Nov'))
    })

    it('upcoming registrations say nothing of the kind and have no "OK"', async () => {
      const wrapper = await mountHome(drawing).mounting

      for (const shown of [line(wrapper, 'Thu 5 Nov'), line(wrapper, 'Sat 14 Nov')]) {
        expect(pageText(shown)).not.toContain('no longer takes place')
        expect(hasControl(shown, 'OK')).toBe(false)
      }
    })

    it('a proposed one has "OK" but no "Confirm"', async () => {
      const wrapper = await mountHome([
        summary(garden, [], null, 'volunteer', [registration('r-12', 'proposed', '2026-11-12')]),
      ]).mounting

      const shown = line(wrapper, 'Thu 12 Nov')
      expect(hasControl(shown, 'OK')).toBe(true)
      expect(hasControl(shown, 'Confirm')).toBe(false)
    })

    it('"OK" cancels the registration, which then no longer shows', async () => {
      let status: Registration['status'] = 'confirmed'
      const calls = mockApi({
        'GET /api/session': signedInAsAlice,
        'GET /api/associations': () => ({
          status: 200,
          body: [
            summary(
              garden,
              [registration('r-5', 'confirmed', '2026-11-05')],
              null,
              'volunteer',
              status === 'cancelled' ? [] : [registration('r-12', status, '2026-11-12')],
            ),
          ],
        }),
        [`PATCH /api/associations/${garden.id}/registrations/r-12`]: (body) => {
          status = (body as { status: Registration['status'] }).status
          return { status: 200, body: registration('r-12', status, '2026-11-12') }
        },
      })
      const wrapper = await mountApp('/')

      await press(line(wrapper, 'Thu 12 Nov'), 'OK')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `/api/associations/${garden.id}/registrations/r-12`,
        body: { status: 'cancelled' },
      })
      const text = pageText(item(wrapper, garden.name))
      expect(text).not.toContain('Thu 12 Nov')
      expect(text).toContain('Thu 5 Nov, 10:00–13:00')
    })
  })

  describe('R14', () => {
    it('reminds of a planning period with no registration of mine', async () => {
      const wrapper = await mountHome(drawing).mounting

      const text = pageText(item(wrapper, repairCafe.name))
      expect(text).toContain('No registration yet for the planning period, 2–25 Nov.')
      expect(hasControl(item(wrapper, repairCafe.name), 'Choose your slots')).toBe(true)
      expect(text).not.toContain('No upcoming registration.')
    })

    it('no reminder when I have a registration in the period', async () => {
      const wrapper = await mountHome(drawing).mounting

      expect(pageText(item(wrapper, garden.name))).not.toContain('No registration yet')
      expect(hasControl(item(wrapper, garden.name), 'Choose your slots')).toBe(false)
    })

    it('no reminder once the period has ended, but "No upcoming registration."', async () => {
      const wrapper = await mountHome([summary(garden, [], period('2026-10-01', '2026-11-03', 0))])
        .mounting

      const text = pageText(item(wrapper, garden.name))
      expect(text).not.toContain('No registration yet')
      expect(text).toContain('No upcoming registration.')
    })

    it('a period ending today still reminds', async () => {
      const wrapper = await mountHome([summary(garden, [], period('2026-10-01', '2026-11-04', 0))])
        .mounting

      expect(pageText(item(wrapper, garden.name))).toContain(
        'No registration yet for the planning period, 1 Oct – 4 Nov.',
      )
    })

    it('after midnight in Paris, a period that ended yesterday no longer reminds', async () => {
      // 00:30 on 5 November in Paris, still 4 November in UTC.
      vi.setSystemTime(new Date('2026-11-04T23:30:00Z'))
      const wrapper = await mountHome([summary(garden, [], period('2026-10-01', '2026-11-04', 0))])
        .mounting

      expect(pageText(item(wrapper, garden.name))).not.toContain('No registration yet')
    })

    it('no reminder when there is no period', async () => {
      const wrapper = await mountHome(drawing).mounting

      expect(pageText(item(wrapper, atelier.name))).not.toContain('No registration yet')
    })

    it('reminds alongside upcoming registrations outside the period', async () => {
      const wrapper = await mountHome([
        summary(
          garden,
          [registration('r-30', 'proposed', '2026-11-30')],
          period('2026-11-02', '2026-11-25', 0),
        ),
      ]).mounting

      const text = pageText(item(wrapper, garden.name))
      expect(text).toContain('Mon 30 Nov, 10:00–13:00 ?')
      expect(text).toContain('No registration yet for the planning period, 2–25 Nov.')
    })

    it('"Choose your slots" leads to the association Schedule', async () => {
      const api = planningApi({
        me: 'u-alice',
        role: 'volunteer',
        members: [member('u-alice', 'Alice', 'volunteer')],
      })
      mockApi({
        'GET /api/session': signedInAsAlice,
        'GET /api/associations': {
          status: 200,
          body: [summary(garden, [], period('2026-11-02', '2026-11-25', 0))],
        },
        ...api.routes,
      })
      const wrapper = await mountApp('/')

      await press(wrapper, 'Choose your slots')

      expect(wrapper.vm.$route.path).toBe(`/associations/${garden.id}`)
    })

    it.each([
      ['2026-11-02', '2026-11-25', '2–25 Nov'],
      ['2026-10-28', '2026-11-25', '28 Oct – 25 Nov'],
      ['2026-12-28', '2027-01-08', '28 Dec 2026 – 8 Jan 2027'],
    ])("the period's dates %s to %s read %s", async (first, last, shown) => {
      const wrapper = await mountHome([summary(garden, [], period(first, last, 0))]).mounting

      expect(pageText(item(wrapper, garden.name))).toContain(
        `No registration yet for the planning period, ${shown}.`,
      )
    })
  })

  it('in French', async () => {
    localStorage.setItem('gilda.locale', 'fr')
    const wrapper = await mountHome(drawing).mounting

    const gardenText = pageText(item(wrapper, garden.name))
    expect(gardenText).toContain("jeu. 12 nov., 10:00–13:00 : ce créneau n'a plus lieu.")
    expect(control(line(wrapper, 'jeu. 12 nov.'), 'OK').exists()).toBe(true)
    expect(gardenText).toContain('jeu. 5 nov., 10:00–13:00')
    expect(gardenText).toContain('sam. 14 nov., 10:00–13:00 ?')
    expect(control(line(wrapper, 'sam. 14 nov.'), 'Confirmer').exists()).toBe(true)
    const repairText = pageText(item(wrapper, repairCafe.name))
    expect(repairText).toContain('Aucune inscription pour la période de planning, 2–25 nov.')
    expect(hasControl(item(wrapper, repairCafe.name), 'Choisir mes créneaux')).toBe(true)
    expect(pageText(item(wrapper, atelier.name))).toContain('Aucune inscription à venir.')
  })
})
