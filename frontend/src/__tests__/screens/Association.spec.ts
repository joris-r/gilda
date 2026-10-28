import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import { control, fill, hasControl, item, mockApi, press, type Route } from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const path = `/associations/${garden.id}`
const membersPath = `/api/associations/${garden.id}/members`

function associationAs(role: 'manager' | 'volunteer', members: ReturnType<typeof member>[]) {
  return { status: 200, body: { ...garden, role, members } }
}

function mountAs(
  role: 'manager' | 'volunteer',
  members: ReturnType<typeof member>[],
  routes: Record<string, Route> = {},
) {
  const calls = mockApi({
    'GET /api/session': signedInAsAlice,
    [`GET /api/associations/${garden.id}`]: associationAs(role, members),
    ...routes,
  })
  return { calls, mounting: mountApp(path) }
}

const alice = member('u-alice', 'Alice', 'manager')
const zoe = member('u-zoe', 'Zoé', 'manager')
const bruno = member('u-bruno', 'Bruno', 'volunteer')
const chloe = member('u-chloe', 'Chloé', 'volunteer', false)

describe('Association', () => {
  it('shows the association name and its members with email and role', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const wrapper = await mounting

    expect(pageText(wrapper)).toContain(garden.name)
    expect(pageText(wrapper)).toContain('Members')
    const line = item(wrapper, 'Bruno')
    expect(line.text()).toContain('bruno@example.org')
    expect(line.text().toLowerCase()).toContain('volunteer')
  })

  it('lists managers first, then by display name', async () => {
    const { mounting } = mountAs('manager', [chloe, zoe, bruno, alice])
    const wrapper = await mounting

    const names = wrapper
      .findAll('li')
      .map((li) => ['Alice', 'Zoé', 'Bruno', 'Chloé'].find((name) => li.text().includes(name)))
      .filter((name) => name !== undefined)
    expect(names).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé'])
  })

  it('marks members without an account with "no account"', async () => {
    const { mounting } = mountAs('manager', [alice, chloe])
    const wrapper = await mounting

    expect(item(wrapper, 'Chloé').text()).toContain('no account')
    expect(item(wrapper, 'Alice').text()).not.toContain('no account')
  })

  describe('as a manager', () => {
    it('offers Change role on each member and the Add a member form', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(hasControl(item(wrapper, 'Bruno'), 'Change role')).toBe(true)
      expect(hasControl(item(wrapper, 'Alice'), 'Change role')).toBe(true)
      expect(pageText(wrapper)).toContain('Add a member')
    })

    it('Change role asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Change role')

      expect(item(wrapper, 'Bruno').text()).toContain('Make Bruno manager?')
      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    })

    it('Confirm changes the role with PATCH and says so', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${membersPath}/u-bruno`]: { status: 200, body: { ...bruno, role: 'manager' } },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Change role')
      await press(item(wrapper, 'Bruno'), 'Confirm')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${membersPath}/u-bruno`,
        body: { role: 'manager' },
      })
      expect(pageText(wrapper)).toContain('Bruno is now manager.')
      expect(item(wrapper, 'Bruno').text().toLowerCase()).toContain('manager')
    })

    it('Cancel leaves the role unchanged', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Change role')
      await press(item(wrapper, 'Bruno'), 'Cancel')

      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Change role')).toBe(true)
    })

    it('demoting the last manager says an association keeps one', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${membersPath}/u-alice`]: { status: 409, body: { error: 'Last manager' } },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Change role')
      expect(item(wrapper, 'Alice').text()).toContain('Make Alice volunteer?')
      await press(item(wrapper, 'Alice'), 'Confirm')

      expect(pageText(wrapper)).toContain('An association keeps at least one manager.')
      expect(item(wrapper, 'Alice').text().toLowerCase()).toContain('manager')
    })

    it('adds a member with POST and says so', async () => {
      let members = [alice]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/${garden.id}`]: () => associationAs('manager', members),
        [`POST ${membersPath}`]: () => {
          members = [alice, chloe]
          return { status: 201, body: chloe }
        },
      })
      const wrapper = await mounting

      await fill(wrapper, 'Display name', 'Chloé')
      await fill(wrapper, 'Email', 'chloé@example.org')
      await fill(wrapper, 'Role', 'volunteer')
      await press(wrapper, 'Add member')

      expect(calls).toContainEqual({
        method: 'POST',
        path: membersPath,
        body: { display_name: 'Chloé', email: 'chloé@example.org', role: 'volunteer' },
      })
      expect(pageText(wrapper)).toContain('Chloé added.')
      expect(item(wrapper, 'chloé@example.org').exists()).toBe(true)
    })

    it('can add a manager', async () => {
      const { calls, mounting } = mountAs('manager', [alice], {
        [`POST ${membersPath}`]: { status: 201, body: zoe },
      })
      const wrapper = await mounting

      await fill(wrapper, 'Display name', 'Zoé')
      await fill(wrapper, 'Email', 'zoé@example.org')
      await fill(wrapper, 'Role', 'manager')
      await press(wrapper, 'Add member')

      expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ role: 'manager' })
    })

    it('says when the person is already a member', async () => {
      const { mounting } = mountAs('manager', [alice, chloe], {
        [`POST ${membersPath}`]: { status: 409, body: { error: 'Already a member' } },
      })
      const wrapper = await mounting

      await fill(wrapper, 'Display name', 'Chloé')
      await fill(wrapper, 'Email', 'chloé@example.org')
      await press(wrapper, 'Add member')

      expect(pageText(wrapper)).toContain('Chloé is already a member.')
    })
  })

  describe('as a volunteer', () => {
    it('shows members and roles without Change role or Add a member', async () => {
      const { mounting } = mountAs('volunteer', [zoe, bruno, alice])
      const wrapper = await mounting

      expect(item(wrapper, 'Zoé').text().toLowerCase()).toContain('manager')
      expect(pageText(wrapper)).not.toContain('Change role')
      expect(pageText(wrapper)).not.toContain('Add a member')
      expect(() => control(wrapper, 'Add member')).toThrow()
    })
  })
})
