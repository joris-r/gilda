import { flushPromises, type DOMWrapper, type VueWrapper } from '@vue/test-utils'
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
import { garden, member, repairCafe, signedInAsAlice } from './fixtures'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const path = `/association/${garden.slug}/members`
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
    [`GET /api/associations/by-slug/${garden.slug}`]: associationAs(role, members),
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
  // /core/ui/header/location
  it('the header shows the association name, then Members', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const text = header(await mounting).text()

    expect(text).toContain(garden.name)
    expect(text.indexOf('Members')).toBeGreaterThan(text.indexOf(garden.name))
  })

  // /core/ui/header/association-link
  it("the association's name leads to its Schedule", async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const wrapper = await mounting

    expect(control(header(wrapper), garden.name).attributes('href')).toBe(
      `/association/${garden.slug}`,
    )
  })

  // /core/ui/header/title
  it('shows no back link', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])

    const text = pageText(await mounting)

    expect(text).toContain('bruno@example.org')
    expect(text).not.toContain('←')
  })

  // /core/ui/members/list
  it('shows its members with email and role', async () => {
    const { mounting } = mountAs('manager', [alice, bruno])
    const wrapper = await mounting

    const line = item(wrapper, 'Bruno')
    expect(line.text()).toContain('bruno@example.org')
    expect(line.text().toLowerCase()).toContain('volunteer')
  })

  // /core/ui/members/list
  it('lists managers first, then by display name', async () => {
    const { mounting } = mountAs('manager', [chloe, zoe, bruno, alice])
    const wrapper = await mounting

    const names = wrapper
      .findAll('li')
      .map((li) => ['Alice', 'Zoé', 'Bruno', 'Chloé'].find((name) => li.text().includes(name)))
      .filter((name) => name !== undefined)
    expect(names).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé'])
  })

  // /core/ui/members/not-joined
  it('marks a member without a password as "not joined yet"', async () => {
    const { mounting } = mountAs('manager', [alice, chloe])
    const wrapper = await mounting

    expect(item(wrapper, 'Chloé').text()).toContain('not joined yet')
    expect(item(wrapper, 'Alice').text()).not.toContain('not joined yet')
  })

  // /core/ui/members/not-joined
  it('marks a member with a password but an unconfirmed email as "not joined yet"', async () => {
    const brunoPending = member('u-bruno', 'Bruno', 'volunteer', true, false)
    const { mounting } = mountAs('manager', [alice, brunoPending])
    const wrapper = await mounting

    expect(item(wrapper, 'Bruno').text()).toContain('not joined yet')
  })

  // /core/ui/members/not-joined
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

    // /core/ui/members/first-five
    it('shows the first 5 members and "Show all 7 members"', async () => {
      const { mounting } = mountAs('manager', seven)
      const wrapper = await mounting

      expect(shownMembers(wrapper, names)).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé', 'David'])
      expect(showsControl(wrapper, 'Show all 7 members')).toBe(true)
    })

    // /core/ui/members/first-five
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

    // /core/ui/members/first-five
    it('with 5 members, shows them all, without the link', async () => {
      const { mounting } = mountAs('manager', [alice, zoe, bruno, chloe, david])
      const wrapper = await mounting

      expect(shownMembers(wrapper, names)).toEqual(['Alice', 'Zoé', 'Bruno', 'Chloé', 'David'])
      expect(pageText(wrapper)).not.toContain('Show all')
    })
  })

  describe('as a manager', () => {
    // /core/ui/members/manager
    it('offers an edit icon on each member, and Add a member', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(hasControl(item(wrapper, 'Bruno'), 'Edit Bruno')).toBe(true)
      expect(hasControl(item(wrapper, 'Alice'), 'Edit Alice')).toBe(true)
      expect(showsControl(wrapper, 'Add a member')).toBe(true)
    })

    // /ui/forms/dialog
    it('shows no form and no line action until one is opened', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(showsField(wrapper, 'Display name')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Change role')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Send link')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Revoke link')).toBe(false)
      expect(hasControl(item(wrapper, 'Bruno'), 'Remove from the association')).toBe(false)
    })

    // /core/ui/members/add /ui/forms/create
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

    // /core/ui/members/add /core/ui/members/added /ui/forms/success
    it('adds a member with POST, closes the dialog and says so', async () => {
      let members = [alice]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/by-slug/${garden.slug}`]: () => associationAs('manager', members),
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

    // /core/ui/members/add
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

    // /core/ui/members/already /ui/forms/failure
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
    // /core/ui/members/edit /ui/forms/edit /ui/forms/icon-names
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

    // /core/ui/members/save /core/ui/members/changed
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

    // /core/ui/members/same-role
    it('Save with the same role closes the dialog and changes nothing', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Save')

      expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
      expect(dialogs(wrapper)).toHaveLength(0)
    })

    // /ui/forms/close
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

    // /core/ui/members/last-manager /ui/forms/failure
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

    // /core/ui/members/revoke-link
    it('shows only for a member with an access link', async () => {
      const { mounting } = mountAs('manager', [alice, brunoWithLink])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(true)
      await press(dialog(wrapper), 'Cancel')

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      expect(hasControl(dialog(wrapper), 'Revoke link')).toBe(false)
    })

    // /core/ui/members/revoke-link /ui/forms/confirmation
    it('asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, brunoWithLink])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      await press(dialog(wrapper), 'Revoke link')

      expect(dialog(wrapper).text()).toContain("Revoke Bruno's sign-in link?")
      expect(hasControl(dialog(wrapper), 'Revoke')).toBe(true)
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /core/ui/members/revoke-link /ui/forms/nested
    it('Revoke revokes it with DELETE, closes both dialogs and says so', async () => {
      let members = [alice, brunoWithLink]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/by-slug/${garden.slug}`]: () => associationAs('manager', members),
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

    // /ui/forms/close
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

    // /core/ui/members/send-link
    it('shows in the dialog of each member', async () => {
      const { mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      expect(hasControl(dialog(wrapper), 'Send link')).toBe(true)
      await press(dialog(wrapper), 'Cancel')

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      expect(hasControl(dialog(wrapper), 'Send link')).toBe(true)
    })

    // /core/ui/members/send-link /ui/forms/confirmation
    it('asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Send link')

      expect(dialog(wrapper).text()).toContain("Send Chloé's sign-in link by email?")
      expect(hasControl(dialog(wrapper), 'Send')).toBe(true)
      expect(calls.some((c) => c.path.endsWith('/access-link'))).toBe(false)
    })

    // /core/ui/members/send-link /core/ui/members/sent /ui/forms/nested
    it('Send sends the link with POST, closes both dialogs and says so', async () => {
      let members = [alice, chloe]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/by-slug/${garden.slug}`]: () => associationAs('manager', members),
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

    // /core/ui/members/not-sent
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

  describe('Remove from the association', () => {
    // /core/ui/members/remove
    it('shows in the dialog of each member', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(item(wrapper, 'Bruno'), 'Edit Bruno')
      expect(hasControl(dialog(wrapper), 'Remove from the association')).toBe(true)
      await press(dialog(wrapper), 'Cancel')

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      expect(hasControl(dialog(wrapper), 'Remove from the association')).toBe(true)
    })

    // /core/ui/members/remove /ui/forms/confirmation
    it('asks for confirmation before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Remove from the association')

      expect(pageText(dialog(wrapper))).toContain(
        'Remove Chloé from the association? Their upcoming registrations are cancelled.',
      )
      expect(hasControl(dialog(wrapper), 'Remove')).toBe(true)
      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    })

    // /core/ui/members/remove /core/ui/members/removed /ui/forms/nested
    it('Remove removes the member with DELETE, closes both dialogs and says so', async () => {
      let members = [alice, chloe]
      const { calls, mounting } = mountAs('manager', [], {
        [`GET /api/associations/by-slug/${garden.slug}`]: () => associationAs('manager', members),
        [`DELETE ${membersPath}/u-chloe`]: () => {
          members = [alice]
          return { status: 204 }
        },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Remove from the association')
      await press(dialog(wrapper), 'Remove')

      expect(calls).toContainEqual({
        method: 'DELETE',
        path: `${membersPath}/u-chloe`,
        body: undefined,
      })
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain('Chloé is removed.')
      expect(pageText(wrapper)).not.toContain('chloé@example.org')
    })

    // /ui/forms/close
    it('Cancel leaves the member', async () => {
      const { calls, mounting } = mountAs('manager', [alice, chloe])
      const wrapper = await mounting

      await press(item(wrapper, 'Chloé'), 'Edit Chloé')
      await press(dialog(wrapper), 'Remove from the association')
      await press(dialog(wrapper), 'Cancel')

      expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
      expect(titleOf(dialog(wrapper))).toBe('Chloé')
    })

    // /core/ui/members/remove-last-manager
    it('removing the last manager says an association keeps one, and changes nothing', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`DELETE ${membersPath}/u-alice`]: { status: 409, body: { error: 'Last manager' } },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      await press(dialog(wrapper), 'Remove from the association')
      await press(dialog(wrapper), 'Remove')

      const text = [pageText(wrapper), ...dialogs(wrapper).map((d) => pageText(d))].join(' ')
      expect(text).toContain('An association keeps at least one manager.')
      expect(text).not.toContain('is removed')
      expect(item(wrapper, 'Alice').exists()).toBe(true)
    })

    // /core/ui/members/themself
    it('a manager who removes themself is led to My associations', async () => {
      const { mounting } = mountAs('manager', [alice, zoe], {
        [`DELETE ${membersPath}/u-alice`]: { status: 204 },
        'GET /api/associations': { status: 200, body: [] },
      })
      const wrapper = await mounting

      await press(item(wrapper, 'Alice'), 'Edit Alice')
      await press(dialog(wrapper), 'Remove from the association')
      await press(dialog(wrapper), 'Remove')

      expect(wrapper.vm.$route.path).toBe('/')
      expect(pageText(wrapper)).toContain('My associations')
    })
  })

  describe('Rename the association', () => {
    const associationPath = `/api/associations/${garden.id}`
    const newName = 'Jardin des Lilas'

    function renames(calls: { method: string; path: string }[]) {
      return calls.filter((c) => c.method === 'PATCH' && c.path === associationPath)
    }

    /** A backend that keeps the new name, however the screen gets it back. */
    function renamingRoutes(): Record<string, Route> {
      let name = garden.name
      return {
        [`GET /api/associations/by-slug/${garden.slug}`]: () => ({
          status: 200,
          body: { ...garden, name, role: 'manager', members: [alice, bruno] },
        }),
        [`PATCH ${associationPath}`]: (body) => {
          name = (body as { name: string }).name
          return { status: 200, body: { id: garden.id, slug: garden.slug, name, role: 'manager' } }
        },
      }
    }

    function nameInput(open: DOMWrapper<Element>) {
      return field(open, 'Name').element as HTMLInputElement
    }

    // /core/ui/members/manager
    it('shows below the members and above "Delete the association", for a manager', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(showsControl(wrapper, 'Rename the association')).toBe(true)
      const text = pageText(wrapper)
      expect(text.indexOf('Rename the association')).toBeGreaterThan(text.indexOf('Bruno'))
      expect(text.indexOf('Rename the association')).toBeLessThan(
        text.indexOf('Delete the association'),
      )
      expect(dialogs(wrapper)).toHaveLength(0)
    })

    // /core/ui/members/rename
    it('opens the dialog with the current name, before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Rename the association')
      expect(nameInput(open).value).toBe(garden.name)
      expect(showsControl(open, 'Save')).toBe(true)
      expect(showsControl(open, 'Cancel')).toBe(true)
      expect(renames(calls)).toHaveLength(0)
    })

    // /core/ui/members/rename
    it('Save is enabled only when Name is not empty', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      const open = dialog(wrapper)
      const isDisabled = () => control(open, 'Save').attributes('disabled') !== undefined

      expect(isDisabled()).toBe(false)
      await fill(open, 'Name', '')
      expect(isDisabled()).toBe(true)
      await fill(open, 'Name', newName)
      expect(isDisabled()).toBe(false)
    })

    // /core/ui/members/rename
    it('submitting an empty Name does not rename', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      const open = dialog(wrapper)
      await fill(open, 'Name', '')
      await press(open, 'Save')

      expect(renames(calls)).toHaveLength(0)
    })

    // /core/ui/members/renamed
    it('Save with another name changes it, updates the header and says so', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      const open = dialog(wrapper)
      await fill(open, 'Name', newName)
      await press(open, 'Save')

      expect(renames(calls).map((c) => c.body)).toEqual([{ name: newName }])
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(control(header(wrapper), newName).attributes('href')).toBe(
        `/association/${garden.slug}`,
      )
      expect(header(wrapper).text()).not.toContain(garden.name)
      expect(pageText(wrapper)).toContain(`The association is now ${newName}.`)
      expect(wrapper.vm.$route.path).toBe(path)
    })

    // /core/ui/members/same-name
    it('Save with the same name closes the dialog and changes nothing', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      await press(dialog(wrapper), 'Save')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(renames(calls)).toHaveLength(0)
      expect(pageText(wrapper)).not.toContain('The association is now')
    })

    // /ui/forms/close
    it('Cancel closes the dialog, changes nothing and forgets the typed name', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      await fill(dialog(wrapper), 'Name', newName)
      await press(dialog(wrapper), 'Cancel')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(renames(calls)).toHaveLength(0)
      expect(header(wrapper).text()).toContain(garden.name)

      await press(wrapper, 'Rename the association')
      expect(nameInput(dialog(wrapper)).value).toBe(garden.name)
    })

    // /core/ui/members/rename
    it('reopening after a rename shows the new name', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      await fill(dialog(wrapper), 'Name', newName)
      await press(dialog(wrapper), 'Save')

      await press(wrapper, 'Rename the association')
      expect(nameInput(dialog(wrapper)).value).toBe(newName)
    })

    // /core/ui/members/delete
    it('after a rename, "Delete the association" asks for the new name', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], renamingRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      await fill(dialog(wrapper), 'Name', newName)
      await press(dialog(wrapper), 'Save')

      await press(wrapper, 'Delete the association')
      const open = dialog(wrapper)
      const confirmField = "Type the association's name to confirm"
      expect(open.text()).toContain(`Delete ${newName}?`)
      await fill(open, confirmField, garden.name)
      expect(control(open, 'Delete').attributes('disabled')).toBeDefined()
      await fill(open, confirmField, newName)
      expect(control(open, 'Delete').attributes('disabled')).toBeUndefined()
    })

    // /ui/forms/failure
    it('when the API refuses, keeps the dialog and the old name', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${associationPath}`]: { status: 403, body: { error: 'Managers only' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      const open = dialog(wrapper)
      await fill(open, 'Name', newName)
      await press(open, 'Save')

      expect(dialogs(wrapper)).toHaveLength(1)
      expect(header(wrapper).text()).toContain(garden.name)
      expect(pageText(wrapper)).not.toContain('The association is now')
    })

    // /ui/errors/generic /ui/forms/failure
    it('a rename that fails says "Something went wrong. Try again." in the dialog', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${associationPath}`]: { status: 500, body: { error: 'Server error' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Rename the association')
      await fill(dialog(wrapper), 'Name', newName)
      await press(dialog(wrapper), 'Save')

      expect(dialog(wrapper).text()).toContain('Something went wrong. Try again.')
    })
  })

  describe('Change the association identifier', () => {
    const associationPath = `/api/associations/${garden.id}`
    const newSlug = 'jardin-des-lilas'
    const newPath = `/association/${newSlug}/members`

    function changes(calls: { method: string; path: string }[]) {
      return calls.filter((c) => c.method === 'PATCH' && c.path === associationPath)
    }

    /** A backend that keeps the new slug: the former one no longer answers. */
    function slugRoutes(): Record<string, Route> {
      let slug = garden.slug
      const read =
        (at: string): Route =>
        () =>
          slug === at
            ? { status: 200, body: { ...garden, slug, role: 'manager', members: [alice, bruno] } }
            : { status: 404, body: { error: 'Not found' } }
      return {
        [`GET /api/associations/by-slug/${garden.slug}`]: read(garden.slug),
        [`GET /api/associations/by-slug/${newSlug}`]: read(newSlug),
        [`PATCH ${associationPath}`]: (body) => {
          slug = (body as { slug: string }).slug
          return { status: 200, body: { id: garden.id, name: garden.name, slug, role: 'manager' } }
        },
      }
    }

    function slugInput(open: DOMWrapper<Element>) {
      return field(open, 'Association identifier').element as HTMLInputElement
    }

    // /core/ui/members/manager
    it('shows between "Rename the association" and "Delete the association", for a manager', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(showsControl(wrapper, 'Change the association identifier')).toBe(true)
      const text = pageText(wrapper)
      expect(text.indexOf('Change the association identifier')).toBeGreaterThan(
        text.indexOf('Rename the association'),
      )
      expect(text.indexOf('Change the association identifier')).toBeLessThan(
        text.indexOf('Delete the association'),
      )
    })

    // /core/ui/members/volunteer
    it('a volunteer does not see it', async () => {
      const { mounting } = mountAs('volunteer', [alice, bruno])
      const wrapper = await mounting

      expect(showsControl(wrapper, 'Change the association identifier')).toBe(false)
    })

    // /core/ui/members/change-slug
    it('opens the dialog with the current slug and its prefix, before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')

      const open = dialog(wrapper)
      expect(titleOf(open)).toBe('Change the association identifier')
      expect(slugInput(open).value).toBe(garden.slug)
      expect(open.text()).toContain('/association/')
      expect(showsControl(open, 'Save')).toBe(true)
      expect(showsControl(open, 'Cancel')).toBe(true)
      expect(changes(calls)).toHaveLength(0)
    })

    // /core/ui/members/change-slug
    it('Save is enabled only when Association identifier is not empty', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      const open = dialog(wrapper)
      const isDisabled = () => control(open, 'Save').attributes('disabled') !== undefined

      expect(isDisabled()).toBe(false)
      await fill(open, 'Association identifier', '')
      expect(isDisabled()).toBe(true)
      await fill(open, 'Association identifier', newSlug)
      expect(isDisabled()).toBe(false)
    })

    // /core/ui/members/slug-changed
    it('Save with another slug changes it, moves to the new URL and says so', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], slugRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      const open = dialog(wrapper)
      await fill(open, 'Association identifier', newSlug)
      await press(open, 'Save')
      await flushPromises()

      expect(changes(calls).map((c) => c.body)).toEqual([{ slug: newSlug }])
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(wrapper.vm.$route.path).toBe(newPath)
      expect(pageText(wrapper)).toContain(`The association identifier is now ${newSlug}.`)
      expect(pageText(wrapper)).toContain('Bruno')
      expect(pageText(wrapper)).not.toContain('This association does not exist')
    })

    // /core/ui/members/slug-changed /core/ui/header/association-link
    it("the header's name then leads to the Schedule at the new slug", async () => {
      const { mounting } = mountAs('manager', [alice, bruno], slugRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      const open = dialog(wrapper)
      await fill(open, 'Association identifier', newSlug)
      await press(open, 'Save')
      await flushPromises()

      expect(control(header(wrapper), garden.name).attributes('href')).toBe(
        `/association/${newSlug}`,
      )
    })

    // /core/ui/members/same-slug
    it('Save with the same slug closes the dialog and changes nothing', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], slugRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      await press(dialog(wrapper), 'Save')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(changes(calls)).toHaveLength(0)
      expect(wrapper.vm.$route.path).toBe(path)
      expect(pageText(wrapper)).not.toContain('The association identifier is now')
    })

    // /ui/forms/close
    it('Cancel closes the dialog, changing nothing', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], slugRoutes())
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      const open = dialog(wrapper)
      await fill(open, 'Association identifier', newSlug)
      await press(open, 'Cancel')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(changes(calls)).toHaveLength(0)
      expect(wrapper.vm.$route.path).toBe(path)
    })

    // /core/ui/members/refused
    it.each([
      [
        400,
        'a malformed slug',
        'Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit.',
      ],
      [409, 'a taken slug', 'This association identifier is already taken.'],
    ])('a %i, for %s, says so and keeps the dialog open', async (status, _case, message) => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`PATCH ${associationPath}`]: { status, body: { error: 'refused' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Change the association identifier')
      const open = dialog(wrapper)
      await fill(open, 'Association identifier', 'Not A Slug')
      await press(open, 'Save')

      expect(dialogs(wrapper)).toHaveLength(1)
      expect(dialog(wrapper).text()).toContain(message)
      expect(wrapper.vm.$route.path).toBe(path)
    })
  })

  describe('Delete the association', () => {
    const associationPath = `/api/associations/${garden.id}`
    const nameField = "Type the association's name to confirm"
    const remaining = {
      ...repairCafe,
      role: 'volunteer',
      upcoming: [],
      obsolete: [],
      planning_period: null,
    }

    function deletions(calls: { method: string; path: string }[]) {
      return calls.filter((c) => c.method === 'DELETE' && c.path === associationPath)
    }

    // /core/ui/members/manager
    it('shows below the members, for a manager', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      expect(showsControl(wrapper, 'Delete the association')).toBe(true)
      const text = pageText(wrapper)
      expect(text.indexOf('Delete the association')).toBeGreaterThan(text.indexOf('Bruno'))
      expect(dialogs(wrapper)).toHaveLength(0)
    })

    // /core/ui/members/delete
    it('asks for confirmation, with the name to type, before calling the API', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')

      const open = dialog(wrapper)
      expect(open.text().replace(/\s+/g, ' ')).toContain(
        `Delete ${garden.name}? Its schedule and its members' registrations are erased. This cannot be undone.`,
      )
      expect(showsField(open, nameField)).toBe(true)
      expect(showsControl(open, 'Delete')).toBe(true)
      expect(showsControl(open, 'Cancel')).toBe(true)
      expect(deletions(calls)).toHaveLength(0)
    })

    // /core/ui/members/delete
    it('Delete is enabled only when the field holds exactly the name', async () => {
      const { mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')
      const open = dialog(wrapper)
      const isDisabled = () => control(open, 'Delete').attributes('disabled') !== undefined

      expect(isDisabled()).toBe(true)
      for (const wrong of ['Jardin', garden.name.toUpperCase(), `${garden.name}!`]) {
        await fill(open, nameField, wrong)
        expect(isDisabled()).toBe(true)
      }
      await fill(open, nameField, garden.name)
      expect(isDisabled()).toBe(false)
    })

    // /core/ui/members/delete
    it('submitting without the exact name does not delete', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], {
        [`DELETE ${associationPath}`]: { status: 204 },
      })
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')
      const open = dialog(wrapper)
      await fill(open, nameField, 'Jardin')
      await press(open, 'Delete')

      expect(deletions(calls)).toHaveLength(0)
      expect(wrapper.vm.$route.path).toBe(path)
    })

    // /core/ui/members/delete
    it('Delete deletes it with DELETE, leads to My associations and says so', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno], {
        [`DELETE ${associationPath}`]: { status: 204 },
        'GET /api/associations': { status: 200, body: [remaining] },
      })
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')
      const open = dialog(wrapper)
      await fill(open, nameField, garden.name)
      await press(open, 'Delete')

      expect(deletions(calls)).toHaveLength(1)
      expect(wrapper.vm.$route.path).toBe('/')
      expect(dialogs(wrapper)).toHaveLength(0)
      expect(pageText(wrapper)).toContain(`${garden.name} is deleted.`)
      expect(item(wrapper, repairCafe.name).exists()).toBe(true)
    })

    // /ui/forms/close
    it('Cancel closes the dialog, changes nothing and forgets the typed name', async () => {
      const { calls, mounting } = mountAs('manager', [alice, bruno])
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')
      await fill(dialog(wrapper), nameField, garden.name)
      await press(dialog(wrapper), 'Cancel')

      expect(dialogs(wrapper)).toHaveLength(0)
      expect(deletions(calls)).toHaveLength(0)
      expect(wrapper.vm.$route.path).toBe(path)

      await press(wrapper, 'Delete the association')
      expect(control(dialog(wrapper), 'Delete').attributes('disabled')).toBeDefined()
    })

    // /ui/forms/failure
    it('when the API refuses, stays on Members and does not say it is deleted', async () => {
      const { mounting } = mountAs('manager', [alice, bruno], {
        [`DELETE ${associationPath}`]: { status: 403, body: { error: 'Managers only' } },
      })
      const wrapper = await mounting

      await press(wrapper, 'Delete the association')
      const open = dialog(wrapper)
      await fill(open, nameField, garden.name)
      await press(open, 'Delete')

      expect(wrapper.vm.$route.path).toBe(path)
      expect(dialogs(wrapper)).toHaveLength(1)
      expect(pageText(wrapper)).not.toContain('is deleted')
    })
  })

  describe('as a volunteer', () => {
    // /core/ui/members/volunteer
    it('shows no "Delete the association"', async () => {
      const { mounting } = mountAs('volunteer', [zoe, bruno])
      const wrapper = await mounting

      expect(hasControl(wrapper, 'Delete the association')).toBe(false)
    })

    // /core/ui/members/volunteer
    it('shows no "Rename the association"', async () => {
      const { mounting } = mountAs('volunteer', [zoe, bruno])
      const wrapper = await mounting

      expect(hasControl(wrapper, 'Rename the association')).toBe(false)
    })

    // /core/ui/members/volunteer /ui/forms/managers
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
      expect(pageText(wrapper)).not.toContain('Remove from the association')
    })
  })
})
