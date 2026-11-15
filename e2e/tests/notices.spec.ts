import { expect, test, type Page } from '@playwright/test'
import { createAssociation, signedIn, uniqueSlug } from './helpers'

const NAME = 'Jardin partagé'

/** Runs `action` on `page` while the answer of the POST it sends is held back; `meanwhile` runs
 * once the server has answered and before the page receives the answer, so the notice is kept
 * and the tab has not yet opened the screen the action leads to. */
async function holdingTheAnswer(
  page: Page,
  action: () => Promise<void>,
  meanwhile: () => Promise<void>,
) {
  await page.route('**/*', async (route) => {
    if (route.request().method() !== 'POST') return route.continue()
    const response = await route.fetch()
    await meanwhile()
    await route.fulfill({ response })
  })
  await action()
}

async function openOtherTab(page: Page, path: string) {
  const other = await page.context().newPage()
  await other.goto(path)
  await expect(other.locator('header').getByText('My associations')).toBeVisible()
  await other.waitForLoadState('networkidle')
  return other
}

test.describe('Notices', () => {
  // /ui/notices/led
  test('the notice of a deletion shows in the tab where it ran, not in another tab that opens the screen first', async ({
    page,
    request,
  }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    await page.goto(`/association/${slug}/members`)
    await page.getByRole('button', { name: 'Delete the association', exact: true }).click()
    const confirmation = page.getByRole('dialog', { name: /^Delete Jardin partagé\?/ })
    await confirmation.getByLabel("Type the association's name to confirm").fill(NAME)

    await holdingTheAnswer(
      page,
      () => confirmation.getByRole('button', { name: 'Delete', exact: true }).click(),
      async () => {
        const other = await openOtherTab(page, '/')
        await expect(other.getByText(`${NAME} is deleted.`)).toHaveCount(0)
        await other.close()
      },
    )

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText(`${NAME} is deleted.`)).toBeVisible()
  })

  // /ui/notices/led
  test('the notice of an identifier change shows on Members in the tab where it ran, not on another screen of another tab', async ({
    page,
    request,
  }) => {
    await signedIn(page, request)
    const slug = await createAssociation(page.request, NAME)
    const changed = uniqueSlug()
    await page.goto(`/association/${slug}/members`)
    await page.getByRole('button', { name: 'Change the association identifier', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Change the association identifier', exact: true })
    await dialog.getByLabel('Association identifier').fill(changed)
    const notice = `The association identifier is now ${changed}.`

    await holdingTheAnswer(
      page,
      () => dialog.getByRole('button', { name: 'Save' }).click(),
      async () => {
        const other = await openOtherTab(page, '/')
        await expect(other.getByText(notice)).toHaveCount(0)
        await other.close()
      },
    )

    await expect(page).toHaveURL(new RegExp(`/association/${changed}/members$`))
    await expect(page.getByText(notice)).toBeVisible()

    await page.goto('/')
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText(notice)).toHaveCount(0)
  })
})
