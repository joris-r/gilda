import { expect, test, type APIRequestContext, type Page } from '@playwright/test'
import { createAssociation, signedIn, uniqueSlug } from './helpers'

const NAME = 'Jardin partagé'
const GENERIC = 'Something went wrong. Try again.'
const MALFORMED =
  'Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit.'
const TAKEN = 'This association identifier is already taken.'
const CONFIRM_DELETE = `Delete ${NAME}? Its schedule and its members' registrations are erased. This cannot be undone.`

/** Alice signs in on `page`, creates an association and opens its Members; returns its slug. */
async function openMembers(page: Page, request: APIRequestContext) {
  await signedIn(page, request)
  const slug = await createAssociation(page.request, NAME)
  await page.goto(`/association/${slug}/members`)
  await expect(page.locator('header').getByText('Members')).toBeVisible()
  return slug
}

/** Switches the interface to French, then reloads the page. */
async function inFrench(page: Page) {
  await page.context().addCookies([{ name: 'language', value: 'fr', url: page.url() }])
  await page.reload()
}

/** Clicks the action `name` on Members and returns the dialog it opens, named `title`. */
async function open(page: Page, name: string, title: string) {
  await page.locator('main').getByRole('button', { name, exact: true }).click()
  const dialog = page.getByRole('dialog', { name: title, exact: true })
  await expect(dialog).toBeVisible()
  return dialog
}

function openRename(page: Page) {
  return open(page, 'Rename the association', 'Rename the association')
}

function openIdentifier(page: Page) {
  return open(page, 'Change the association identifier', 'Change the association identifier')
}

function openDelete(page: Page) {
  return open(page, 'Delete the association', CONFIRM_DELETE)
}

test.describe('Members: Rename the association', () => {
  // /core/ui/members/rename
  // /ui/forms/dialog
  test('its dialog shows the name, with Save enabled only when Name is not empty', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openRename(page)

    const name = dialog.getByLabel('Name', { exact: true })
    await expect(name).toHaveValue(NAME)
    await expect(dialog.getByRole('button', { name: 'Close' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeEnabled()
    await name.fill('')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  // /core/ui/members/renamed
  // /core/operations/update-association/renamed
  // /ui/forms/success
  test('Save with another name closes the dialog, says so and updates the header', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openRename(page)
    await dialog.getByLabel('Name', { exact: true }).fill('Jardin des Lilas')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText('The association is now Jardin des Lilas.')).toBeVisible()
    await expect(page.locator('header').getByRole('link', { name: 'Jardin des Lilas' })).toBeVisible()
    await page.reload()
    await expect(page.locator('header').getByRole('link', { name: 'Jardin des Lilas' })).toBeVisible()
    await expect((await openRename(page)).getByLabel('Name', { exact: true })).toHaveValue(
      'Jardin des Lilas',
    )
  })

  // /core/ui/members/same-name
  test('Save with the same name closes the dialog and says nothing', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openRename(page)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page.getByText(/is now/)).toHaveCount(0)
  })

  // /ui/forms/close
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    await openMembers(page, request)

    const dialog = await openRename(page)
    await dialog.getByLabel('Name', { exact: true }).fill('Jardin des Lilas')
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(page.locator('header').getByRole('link', { name: NAME })).toBeVisible()
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openMembers(page, request)
    await page.route('**/rename', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const dialog = await openRename(page)
    await dialog.getByLabel('Name', { exact: true }).fill('Jardin des Lilas')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(dialog.getByLabel('Name', { exact: true })).toHaveValue('Jardin des Lilas')
  })
})

test.describe('Members: Change the association identifier', () => {
  // /core/ui/members/change-slug
  test('its dialog shows the slug, with Save enabled only when it is not empty', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const dialog = await openIdentifier(page)

    const field = dialog.getByLabel('Association identifier')
    await expect(field).toHaveValue(slug)
    await expect(dialog).toContainText('/association/')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeEnabled()
    await field.fill('')
    await expect(dialog.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  // /core/ui/members/slug-changed
  // /core/operations/update-association/new-slug
  test('Save with another slug moves the screen to its new URL and says so', async ({ page, request }) => {
    await openMembers(page, request)
    const slug = uniqueSlug()

    const dialog = await openIdentifier(page)
    await dialog.getByLabel('Association identifier').fill(slug)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(page).toHaveURL(new RegExp(`/association/${slug}/members$`))
    await expect(page.getByText(`The association identifier is now ${slug}.`)).toBeVisible()
    await expect(page.locator('header').getByText('Members')).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  // /core/ui/members/same-slug
  test('Save with the same slug closes the dialog and says nothing', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const dialog = await openIdentifier(page)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog).toBeHidden()
    await expect(page).toHaveURL(new RegExp(`/association/${slug}/members$`))
    await expect(page.getByText(/is now/)).toHaveCount(0)
  })

  // /core/ui/members/refused
  // /core/ui/new-association/malformed
  // /ui/errors/kept
  test('a malformed slug shows its message in the dialog, keeping what was typed', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const dialog = await openIdentifier(page)
    await dialog.getByLabel('Association identifier').fill('Not A Slug')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(MALFORMED)).toBeVisible()
    await expect(dialog.getByLabel('Association identifier')).toHaveValue('Not A Slug')
    await expect(page).toHaveURL(new RegExp(`/association/${slug}/members$`))
  })

  // /core/ui/members/refused
  // /core/ui/new-association/taken
  test('a taken slug shows its message in the dialog', async ({ page, request }) => {
    await openMembers(page, request)
    const taken = uniqueSlug()
    await createAssociation(page.request, 'Repair Café', taken)

    const dialog = await openIdentifier(page)
    await dialog.getByLabel('Association identifier').fill(taken)
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(TAKEN)).toBeVisible()
  })

  // /ui/forms/close
  test('Cancel closes it, changing nothing', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const dialog = await openIdentifier(page)
    await dialog.getByLabel('Association identifier').fill(uniqueSlug())
    await dialog.getByRole('button', { name: 'Cancel' }).click()

    await expect(dialog).toBeHidden()
    await page.reload()
    await expect(page).toHaveURL(new RegExp(`/association/${slug}/members$`))
    await expect(page.locator('header').getByText('Members')).toBeVisible()
  })

  // /ui/forms/failure
  // /ui/errors/generic
  // /ui/errors/kept
  test('when the server fails: the generic error in the dialog', async ({ page, request }) => {
    await openMembers(page, request)
    await page.route('**/identifier', (route) => route.abort())

    const dialog = await openIdentifier(page)
    await dialog.getByLabel('Association identifier').fill('jardin-des-lilas')
    await dialog.getByRole('button', { name: 'Save' }).click()

    await expect(dialog.getByText(GENERIC)).toBeVisible()
    await expect(dialog.getByLabel('Association identifier')).toHaveValue('jardin-des-lilas')
  })

  // /core/ui/members/slug-changed
  test('the message follows the language', async ({ page, request }) => {
    await openMembers(page, request)
    await inFrench(page)
    const slug = uniqueSlug()

    const dialog = await open(
      page,
      "Modifier l'identifiant de l'association",
      "Modifier l'identifiant de l'association",
    )
    await dialog.getByRole('textbox').fill(slug)
    await dialog.getByRole('button', { name: 'Enregistrer' }).click()

    await expect(page.getByText(`L'identifiant de l'association est désormais ${slug}.`)).toBeVisible()
  })
})

test.describe('Members: Delete the association', () => {
  // /core/ui/members/delete
  test('Delete is enabled only when the field holds exactly the name', async ({ page, request }) => {
    await openMembers(page, request)

    const confirmation = await openDelete(page)
    const field = confirmation.getByLabel("Type the association's name to confirm")
    const deleteButton = confirmation.getByRole('button', { name: 'Delete', exact: true })

    await expect(deleteButton).toBeDisabled()
    await field.fill('Jardin')
    await expect(deleteButton).toBeDisabled()
    await field.fill('jardin partagé')
    await expect(deleteButton).toBeDisabled()
    await field.fill(`${NAME} `)
    await expect(deleteButton).toBeDisabled()
    await field.fill(NAME)
    await expect(deleteButton).toBeEnabled()
  })

  // /core/ui/members/delete
  // /core/operations/delete-association/deleted
  // /core/ui/unknown-association/shown
  test('confirming deletes it, leads to My associations and says so', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const confirmation = await openDelete(page)
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator('header').getByText('My associations')).toBeVisible()
    await expect(page.getByText(`${NAME} is deleted.`)).toBeVisible()
    await expect(page.locator('main').getByRole('link', { name: NAME, exact: true })).toHaveCount(0)
    await page.goto(`/association/${slug}/members`)
    await expect(
      page.getByText('This association does not exist or you are not a member.'),
    ).toBeVisible()
  })

  // /ui/forms/cancel
  test('Cancel changes nothing', async ({ page, request }) => {
    const slug = await openMembers(page, request)

    const confirmation = await openDelete(page)
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Cancel' }).click()

    await expect(confirmation).toBeHidden()
    await page.goto(`/association/${slug}/members`)
    await expect(page.locator('header').getByText('Members')).toBeVisible()
  })

  // /ui/forms/failure
  // /ui/errors/generic
  test('when the server fails: the generic error in the confirmation', async ({ page, request }) => {
    await openMembers(page, request)
    await page.route('**/delete', (route) => route.fulfill({ status: 500, body: 'failure' }))

    const confirmation = await openDelete(page)
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)
    await confirmation.getByRole('button', { name: 'Delete', exact: true }).click()

    await expect(confirmation.getByText(GENERIC)).toBeVisible()
    await expect(confirmation).toContainText(CONFIRM_DELETE)
  })

  // /core/ui/members/delete
  test('the message follows the language', async ({ page, request }) => {
    await openMembers(page, request)
    await inFrench(page)

    const confirmation = await open(
      page,
      "Supprimer l'association",
      `Supprimer ${NAME} ? Son planning et les inscriptions de ses membres sont effacés. Cette action est irréversible.`,
    )
    await confirmation.getByRole('textbox').fill(NAME)
    await confirmation.getByRole('button', { name: 'Supprimer', exact: true }).click()

    await expect(page.getByText(`${NAME} est supprimée.`)).toBeVisible()
  })
})
