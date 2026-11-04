import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
  control,
  field,
  fill,
  hasControl,
  header,
  item,
  mockApi,
  openUserMenu,
  press,
  showsField,
  signedOut,
} from '../mockApi'
import { garden, member, repairCafe, signedInAsAlice, alice } from './fixtures'
import { planningApi } from './planningFake'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const myAssociations = {
  status: 200,
  body: [
    { ...garden, role: 'manager', upcoming: [], obsolete: [], planning_period: null },
    { ...repairCafe, role: 'volunteer', upcoming: [], obsolete: [], planning_period: null },
  ],
}

describe('My associations', () => {
  it('lists my associations with my role in each', async () => {
    mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })

    const wrapper = await mountApp('/')

    expect(header(wrapper).text()).toContain('My associations')
    expect(item(wrapper, garden.name).text().toLowerCase()).toContain('manager')
    expect(item(wrapper, repairCafe.name).text().toLowerCase()).toContain('volunteer')
  })

  it('says when I am in no association', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
    })

    const text = pageText(await mountApp('/'))

    expect(text).toContain('You are not a member of any association yet.')
  })

  it('shows my display name, not my email', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
    })

    const text = pageText(await mountApp('/'))

    expect(text).toContain('Alice')
    expect(text).not.toContain(alice.email)
  })

  it('leads from a name to the association Schedule', async () => {
    const api = planningApi({
      me: 'u-alice',
      role: 'manager',
      members: [member('u-alice', 'Alice', 'manager')],
    })
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': myAssociations,
      ...api.routes,
    })
    const wrapper = await mountApp('/')

    await press(wrapper, garden.name)

    expect(wrapper.vm.$route.path).toBe(`/association/${garden.slug}`)
    expect(hasControl(wrapper, 'Schedule settings')).toBe(true)
  })

  it('"New association", below the list, leads to /association/new', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': myAssociations,
    })
    const wrapper = await mountApp('/')

    const button = control(wrapper, 'New association')
    const lastItem = item(wrapper, repairCafe.name)
    expect(
      lastItem.element.compareDocumentPosition(button.element) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()

    await press(wrapper, 'New association')

    expect(wrapper.vm.$route.path).toBe('/association/new')
  })

  it('shows no form and no "Create an association"', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': myAssociations,
    })
    const wrapper = await mountApp('/')

    expect(showsField(wrapper, 'Name')).toBe(false)
    expect(hasControl(wrapper, 'Create an association')).toBe(false)
  })

  it('Sign out calls DELETE /api/session and shows Sign in', async () => {
    let signedIn = true
    const calls = mockApi({
      'GET /api/session': () => (signedIn ? signedInAsAlice : signedOut),
      'GET /api/associations': { status: 200, body: [] },
      'DELETE /api/session': () => {
        signedIn = false
        return { status: 204 }
      },
    })
    const wrapper = await mountApp('/')

    await openUserMenu(wrapper, 'Alice')
    await press(wrapper, 'Sign out')

    expect(calls).toContainEqual({ method: 'DELETE', path: '/api/session', body: undefined })
    expect(pageText(wrapper)).toContain('No account yet?')
  })
})

describe('New association', () => {
  it('the header shows My associations, leading to /, then New association', async () => {
    mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
    const wrapper = await mountApp('/association/new')

    const text = header(wrapper).text()
    expect(text.indexOf('New association')).toBeGreaterThan(text.indexOf('My associations'))
    expect(control(header(wrapper), 'My associations').attributes('href')).toBe('/')
  })

  it('shows Name, Association identifier with its prefix, and Create association', async () => {
    mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
    const wrapper = await mountApp('/association/new')

    expect(pageText(wrapper)).toContain('New association')
    expect(showsField(wrapper, 'Name')).toBe(true)
    expect(showsField(wrapper, 'Association identifier')).toBe(true)
    expect(pageText(wrapper)).toContain('/association/')
    expect(hasControl(wrapper, 'Create association')).toBe(true)
  })

  function identifier(wrapper: Parameters<typeof field>[0]) {
    return (field(wrapper, 'Association identifier').element as HTMLInputElement).value
  }

  describe('R35', () => {
    it.each([
      ['Repair Café Belleville', 'repair-cafe-belleville'],
      ["L'Atelier  d'à côté !", 'l-atelier-d-a-cote'],
      ['  Élan 2 -- Vélos  ', 'elan-2-velos'],
      ['a'.repeat(60), 'a'.repeat(50)],
      [`${'a'.repeat(49)} b`, 'a'.repeat(49)],
      ['!!!', ''],
    ])('Name %j gives %j', async (name, slug) => {
      mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
      const wrapper = await mountApp('/association/new')

      await fill(wrapper, 'Name', name)

      expect(identifier(wrapper)).toBe(slug)
    })

    it('Association identifier follows Name as it changes', async () => {
      mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
      const wrapper = await mountApp('/association/new')

      await fill(wrapper, 'Name', 'Repair')
      await fill(wrapper, 'Name', 'Repair Café')

      expect(identifier(wrapper)).toBe('repair-cafe')
    })

    it('Association identifier no longer follows Name once the user edits it', async () => {
      mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
      const wrapper = await mountApp('/association/new')

      await fill(wrapper, 'Name', 'Repair')
      await fill(wrapper, 'Association identifier', 'mon-atelier')
      await fill(wrapper, 'Name', 'Repair Café')

      expect(identifier(wrapper)).toBe('mon-atelier')
    })
  })

  it('Create association is enabled only when both fields are not empty', async () => {
    mockApi({ 'GET /api/session': signedInAsAlice, 'GET /api/associations': myAssociations })
    const wrapper = await mountApp('/association/new')
    const isDisabled = () =>
      control(wrapper, 'Create association').attributes('disabled') !== undefined

    expect(isDisabled()).toBe(true)
    await fill(wrapper, 'Name', repairCafe.name)
    expect(isDisabled()).toBe(false)
    await fill(wrapper, 'Association identifier', '')
    expect(isDisabled()).toBe(true)
    await fill(wrapper, 'Association identifier', 'mon-atelier')
    await fill(wrapper, 'Name', '')
    expect(isDisabled()).toBe(true)
  })

  it('sends the identifier the user edited and opens the Schedule at it', async () => {
    const edited = { ...repairCafe, slug: 'mon-atelier' }
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'POST /api/associations': { status: 201, body: { ...edited, role: 'manager' } },
      'GET /api/associations/by-slug/mon-atelier': {
        status: 200,
        body: { ...edited, role: 'manager', members: [member('u-alice', 'Alice', 'manager')] },
      },
    })
    const wrapper = await mountApp('/association/new')

    await fill(wrapper, 'Name', repairCafe.name)
    await fill(wrapper, 'Association identifier', 'mon-atelier')
    await press(wrapper, 'Create association')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/associations',
      body: { name: repairCafe.name, slug: 'mon-atelier' },
    })
    expect(wrapper.vm.$route.path).toBe('/association/mon-atelier')
  })

  it.each([
    [
      400,
      'a malformed slug',
      'Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit.',
    ],
    [409, 'a taken slug', 'This association identifier is already taken.'],
  ])('a %i, for %s, says so and stays on the form', async (status, _case, message) => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'POST /api/associations': { status, body: { error: 'refused' } },
    })
    const wrapper = await mountApp('/association/new')

    await fill(wrapper, 'Name', repairCafe.name)
    await press(wrapper, 'Create association')

    expect(pageText(wrapper)).toContain(message)
    expect(wrapper.vm.$route.path).toBe('/association/new')
    expect(identifier(wrapper)).toBe(repairCafe.slug)
  })

  it('creates an association with POST /api/associations and opens its Schedule', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
      'POST /api/associations': { status: 201, body: { ...repairCafe, role: 'manager' } },
      [`GET /api/associations/by-slug/${repairCafe.slug}`]: {
        status: 200,
        body: { ...repairCafe, role: 'manager', members: [member('u-alice', 'Alice', 'manager')] },
      },
    })
    const wrapper = await mountApp('/')

    await press(wrapper, 'New association')
    await fill(wrapper, 'Name', repairCafe.name)
    await press(wrapper, 'Create association')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/associations',
      body: { name: repairCafe.name, slug: repairCafe.slug },
    })
    expect(wrapper.vm.$route.path).toBe(`/association/${repairCafe.slug}`)
    expect(header(wrapper).text()).toContain(repairCafe.name)
  })

  it('Cancel leads to My associations, creating nothing', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': myAssociations,
    })
    const wrapper = await mountApp('/association/new')

    await fill(wrapper, 'Name', repairCafe.name)
    await press(wrapper, 'Cancel')

    expect(wrapper.vm.$route.path).toBe('/')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
  })

  it('signed out, shows Sign in', async () => {
    mockApi({ 'GET /api/session': signedOut })
    const wrapper = await mountApp('/association/new')

    expect(pageText(wrapper)).toContain('No account yet?')
  })
})
