import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountApp, pageText } from '../mountApp'
import {
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
    { ...garden, role: 'manager' },
    { ...repairCafe, role: 'volunteer' },
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

    expect(wrapper.vm.$route.path).toBe(`/associations/${garden.id}`)
    expect(hasControl(wrapper, 'Schedule settings')).toBe(true)
  })

  it('"+", named "Create an association", shows the form', async () => {
    mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': myAssociations,
    })
    const wrapper = await mountApp('/')

    expect(showsField(wrapper, 'Name')).toBe(false)

    await press(wrapper, 'Create an association')

    expect(showsField(wrapper, 'Name')).toBe(true)
    expect(hasControl(wrapper, 'Create association')).toBe(true)
  })

  it('creates an association with POST /api/associations and opens its page', async () => {
    const calls = mockApi({
      'GET /api/session': signedInAsAlice,
      'GET /api/associations': { status: 200, body: [] },
      'POST /api/associations': { status: 201, body: { ...repairCafe, role: 'manager' } },
      [`GET /api/associations/${repairCafe.id}`]: {
        status: 200,
        body: { ...repairCafe, role: 'manager', members: [member('u-alice', 'Alice', 'manager')] },
      },
    })
    const wrapper = await mountApp('/')

    await press(wrapper, 'Create an association')
    await fill(wrapper, 'Name', repairCafe.name)
    await press(wrapper, 'Create association')

    expect(calls).toContainEqual({
      method: 'POST',
      path: '/api/associations',
      body: { name: repairCafe.name },
    })
    expect(wrapper.vm.$route.path).toBe(`/associations/${repairCafe.id}`)
    expect(header(wrapper).text()).toContain(repairCafe.name)
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
