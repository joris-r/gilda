import type { DOMWrapper, VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
  control,
  dialog,
  dialogs,
  field,
  fill,
  hasControl,
  header,
  item,
  mockApi,
  press,
  showsControl,
  showsField,
  titleOf,
  type Route,
} from '../mockApi'
import { garden, member, signedInAsAlice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const path = `/associations/${garden.id}/members`
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

/** The selected option's text of a selector. */
function shown(select: DOMWrapper<Element>) {
  const element = select.element as HTMLSelectElement
  return element.options[element.selectedIndex]?.text.trim()
}

/** The display names of the visible members, in order. */
function shownMembers(wrapper: VueWrapper, names: string[]) {
  return wrapper
    .findAll('li')
    .filter((li) => li.isVisible())
    .map((li) => names.find((name) => li.text().includes(name)))
    .filter((name) => name !== undefined)
}

describe('Members', () => {
  it('the header shows the association name, then Members', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const text = header(await mounting).text()

    expect(text).toContain(garden.name)
    expect(text.indexOf('Members')).toBeGreaterThan(text.indexOf(garden.name))
  })

  it("the association's name leads to its Schedule", async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const wrapper = await mounting

    expect(control(header(wrapper), garden.name).attributes('href')).toBe(
      `/associations/${garden.id}`,
    )
  })

  it('shows no back link', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])

    const text = pageText(await mounting)

    expect(text).toContain('bruno@example.org')
    expect(text).not.toContain('←')
  })

  it('shows its members with email and role', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const wrapper = await mounting

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

  it('marks a member without a password as "not joined yet"', async () => {
    const { mounting } = mountAs('manager', [alice, chloe])
    const wrapper = await mounting

    expect(item(wrapper, 'Chloé').text()).toContain('not joined yet')
    expect(item(wrapper, 'Alice').text()).not.toContain('not joined yet')
  })

  it('marks a member with a password but an unconfirmed email as "not joined yet"', async () => {
    const brunoPending = member('u-bruno', 'Bruno', 'volunteer', true, false)
    const { mounting } = mountAs('manager', [alice, brunoPending])
    const wrapper = await mounting

    expect(item(wrapper, 'Bruno').text()).toContain('not joined yet')
  })

  it('does not mark a member without a password whose email is confirmed', async () => {
    const chloeByLink = member('u-chloe', 'Chloé', 'volunteer', false, true, true)
    const { mounting } = mountAs('manager', [alice, chloeByLink])
    const wrapper = await mounting

    expect(item(wrapper, 'Chloé').text()).not.toContain('not joined yet')
    expect(item(wrapper, 'Chloé').text()).not.toContain('no account')
  })

  describe('member list', () => {
    const david = member('u-david', 'David', 'volunteer')
    const emma = member('u-emma', 'Emma', 'volunteer')
    const fanny = member('u-fanny', 'Fanny', 'volunteer')
    const names = ['Alice', 'Bruno', 'Chloé', 'David', 'Emma', 'Fanny', 'Zoé']
    const seven = [alice, zoe, bruno, chloe, david, emma, fanny]

    it('shows the first 5 members and "Show all 7 members"', async () => {
      const { mounting } = mountAs('manager', seven)
      const wrapper = await mounting

      expect(shownMembers(wrapper, names)).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé', 'David'])
      expect(showsControl(wrapper, 'Show all 7 members')).toBe(true)
    })

    it('"Show all 7 members" shows the others', async () => {
      const { mounting } = mountAs('manager', seven)
      const wrapper = await mounting

      await press(wrapper, 'Show all 7 members')

      expect(shownMembers(wrapper, names)).toEqual([
        'Alice',
        'Zoé',
        'Bruno',
        'Chloé',
        'David',
        'Emma',
        'Fanny',
      ])
    })

    it('with 5 members, shows them all, without the link', async () => {
      const { mounting } = mountAs('manager', [alice, zoe, bruno, chloe, david])
      const wrapper = await mounting

      expect(shownMembers(wrapper, names)).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé', 'David'])
      expect(pageText(wrapper)).not.toContain('Show all')
    })
  })

  describe('as a manager', () => {
    it('offers an edit icon on each member, and Add a member', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(hasControl(item(wrapper, 'Bruno'), 'Edit Bruno')).toBe(true)
      expect(hasControl(item(wrapper, 'Alice'), 'Edit Alice')).toBe(true)
      expect(showsControl(wrapper, 'Add a member')).toBe(true)
    })

    it('shows no form and no line action until one is opened', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(showsField(wrapper, 'Display name')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Change role')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Send link')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Revoke link')).toBe(false)
    })

    it('"Add a member" opens the dialog "Add a member", Role at Volunteer', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Add a member')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Add a member')
      expect(showsField(open, 'Display name')).toBe(true)
      expect(showsField(open, 'Email')).toBe(true)
      expect(shown(field(open, 'Role'))).toBe('Volunteer')
      expect(showsControl(open, 'Add member')).toBe(true)
    })

    it('adds a member with POST, closes the dialog and says so', async () => {
      let members = [alice]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/${garden.id}`]: () => associationAs('manager', members),
        [`POST ${membersPath}`]: () => {
          members = [alice, chloe]
          return { status: 201, body: chloe }
        },
      })
      const wrapper = await mounting

      await press(wrapper, 'Add a member')
      const open = dialog(wrapper)
      await fill(open, 'Display name', 'Chloé')
      await fill(open, 'Email', 'chloé@example.org')
      await fill(open, 'Role', 'volunteer')
      await press(open, 'Add member')

      expect(calls).toContainEqual({
        method: 'POST',
        path: membersPath,
        body: { display_name: 'Chloé', email: 'chloé@example.org', role: 'volunteer' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain('Chloé added.')
      expect(item(wrapper, 'chloé@example.org').exists()).toBe(true)
    })

    it('can add a manager', async () => {
      const { calls, mounting } = mountAs('manager', [alice], {
        [`POST ${membersPath}`]: { status: 201, body: zoe },
      })
      const wrapper = await mounting

      await press(wrapper, 'Add a member')
      const open = dialog(wrapper)
      await fill(open, 'Display name', 'Zoé')
      await fill(open, 'Email', 'zoé@example.org')
      await fill(open, 'Role', 'manager')
      await press(open, 'Add member')

      expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ role: 'manager' })
    })

    it('says in the dialog when the person is already a member', async () => {
      const { mounting } = mountAs('manager', [alice, chloe], {
        [`POST ${membersPath}`]: { status: 409, body: { error: 'Already a member' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Add a member')
      await fill(dialog(wrapper), 'Display name', 'Chloé')
      await fill(dialog(wrapper), 'Email', 'chloé@example.org')
      await press(dialog(wrapper), 'Add member')

      expect(titleOf(dialog(wrapper))).toBe('Add a member')
      expect(dialog(wrapper).text()).toContain('Chloé is already a member.')
    })
  })

  describe('the edit dialog', () => {
    it('"Edit Bruno" opens the dialog "Bruno", with his email and role', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Bruno')
      expect(open.text()).toContain('bruno@example.org')
      expect(shown(field(open, 'Role'))).toBe('Volunteer')
      expect(showsControl(open, 'Save')).toBe(true)
      expect(showsControl(open, 'Send link')).toBe(true)
    })

    it('Save with another role changes it with PATCH and says so', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${membersPath}/u-bruno`]: { status: 200, body: { ...bruno, role: 'manager' } },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await fill(dialog(wrapper), 'Role', 'manager')
      await press(dialog(wrapper), 'Save')

      expect(calls).toContainEqual({
        method: 'PATCH',
        path: `${membersPath}/u-bruno`,
        body: { role: 'manager' },
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain('Bruno is now manager.')
      expect(item(wrapper, 'Bruno').text().toLowerCase()).toContain('manager')
    })

    it('Save with the same role closes the dialog and changes nothing', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Save')

      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
      expect(dialogs(wrapper)).toHaveLength(0)
    })

    it('Cancel closes the dialog and leaves the role unchanged', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await fill(dialog(wrapper), 'Role', 'manager')
      await press(dialog(wrapper), 'Cancel')

      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(item(wrapper, 'Bruno').text().toLowerCase()).toContain('volunteer')
    })

    it('demoting the last manager says, in the dialog, that an association keeps one', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${membersPath}/u-alice`]: { status: 409, body: { error: 'Last manager' } },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      await fill(dialog(wrapper), 'Role', 'volunteer')
      await press(dialog(wrapper), 'Save')

      expect(dialog(wrapper).text()).toContain('An association keeps at least one manager.')
      expect(item(wrapper, 'Alice').text().toLowerCase()).toContain('manager')
    })
  })

  describe('Revoke link', () => {
    const brunoWithLink = member('u-bruno', 'Bruno', 'volunteer', true, true, true)

    it('shows only for a member with an access link', async () => {
      const { mounting } = mountAs('manager', [alice, brunoWithLink])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(true)
      await press(dialog(wrapper), 'Cancel')

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(false)
    })

    it('asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, brunoWithLink])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Revoke link')

      expect(dialog(wrapper).text()).toContain("Revoke Bruno's sign-in link?")
      expect(hasControl(dialog(wrapper), 'Revoke')).toBe(true)
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    it('Revoke revokes it with DELETE, closes both dialogs and says so', async () => {
      let members = [alice, brunoWithLink]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/${garden.id}`]: () => associationAs('manager', members),
        [`DELETE ${membersPath}/u-bruno/access-link`]: () => {
          members = [alice, bruno]
          return { status: 204 }
        },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Revoke link')
      await press(dialog(wrapper), 'Revoke')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${membersPath}/u-bruno/access-link`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain("Bruno's sign-in link is revoked.")

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(false)
    })

    it('Cancel leaves the link', async () => {
      const { calls, mounting } = mountAs('manager', [alice, brunoWithLink])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Revoke link')
      await press(dialog(wrapper), 'Cancel')

      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
      expect(titleOf(dialog(wrapper))).toBe('Bruno')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(true)
    })
  })

  describe('Send link', () => {
    const chloeWithLink = member('u-chloe', 'Chloé', 'volunteer', false, false, true)

    it('shows in the dialog of each member', async () => {
      const { mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      expect(hasControl(dialog(wrapper), 'Send link')).toBe(true)
      await press(dialog(wrapper), 'Cancel')

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      expect(hasControl(dialog(wrapper), 'Send link')).toBe(true)
    })

    it('asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Send link')

      expect(dialog(wrapper).text()).toContain("Send Chloé's sign-in link by email?")
      expect(hasControl(dialog(wrapper), 'Send')).toBe(true)
      expect(calls.some((c) => c.path.endsWith('/access-link'))).toBe(false)
    })

    it('Send sends the link with POST, closes both dialogs and says so (R26)', async () => {
      let members = [alice, chloe]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/${garden.id}`]: () => associationAs('manager', members),
        [`POST ${membersPath}/u-chloe/access-link`]: () => {
          members = [alice, chloeWithLink]
          return { status: 200, body: chloeWithLink }
        },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Send link')
      await press(dialog(wrapper), 'Send')

      expect(calls).toContainEqual({
        method: 'POST',
        path: `${membersPath}/u-chloe/access-link`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain("Chloé's sign-in link is sent.")

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(true)
    })

    it('says when the email cannot be sent', async () => {
      const { mounting } = mountAs('manager', [alice, chloe], {
        [`POST ${membersPath}/u-chloe/access-link`]: {
          status: 503,
          body: { error: 'Email unavailable' },
        },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Send link')
      await press(dialog(wrapper), 'Send')

      const text = [pageText(wrapper), ...dialogs(wrapper).map((d) => pageText(d))].join(' ')
      expect(text).toContain("We couldn't send Chloé's sign-in link. Try again later.")
      expect(text).not.toContain('link is sent')
    })
  })

  describe('as a volunteer', () => {
    it('shows members and roles without Add a member or the edit icons', async () => {
      const brunoWithLink = member('u-bruno', 'Bruno', 'volunteer', true, true, true)
      const { mounting } = mountAs('volunteer', [zoe, brunoWithLink, alice])
      const wrapper = await mounting

      expect(item(wrapper, 'Zoé').text().toLowerCase()).toContain('manager')
      expect(hasControl(wrapper, 'Add a member')).toBe(false)
      expect(hasControl(wrapper, 'Edit Zoé')).toBe(false)
      expect(hasControl(wrapper, 'Edit Bruno')).toBe(false)
      expect(pageText(wrapper)).not.toContain('Send link')
      expect(pageText(wrapper)).not.toContain('Revoke link')
    })
  })
})
