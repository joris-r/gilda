import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { createAssociation, signedIn, uniqueEmail } from "./helpers";

const GENERIC = "Something went wrong. Try again.";

/** Alice signs in on `page`, creates an association and opens its Members; returns its slug. */
async function openMembers(page: Page, request: APIRequestContext) {
  await signedIn(page, request);
  const slug = await createAssociation(page.request);
  await page.goto(`/association/${slug}/members`);
  await expect(page.locator("header").getByText("Members")).toBeVisible();
  return slug;
}

async function openAdd(page: Page) {
  await page.getByRole("button", { name: "Add a member" }).click();
  const dialog = page.getByRole("dialog", { name: "Add a member" });
  await expect(dialog).toBeVisible();
  return dialog;
}

async function fillAdd(page: Page, displayName: string, email: string) {
  const dialog = await openAdd(page);
  await dialog.getByLabel("Display name", { exact: true }).fill(displayName);
  await dialog.getByLabel("Email", { exact: true }).fill(email);
  return dialog;
}

function line(page: Page, text: string) {
  return page.locator("main").getByRole("listitem").filter({ hasText: text });
}

test.describe("Members", () => {
  test("the header's association name leads to its Schedule", async ({
    page,
    request,
  }) => {
    const slug = await openMembers(page, request);

    await page
      .locator("header")
      .getByRole("link", { name: "Jardin partagé" })
      .click();

    await expect(page).toHaveURL(new RegExp(`/association/${slug}$`));
  });

  test('"Show all 7 members" shows the others', async ({ page, request }) => {
    await openMembers(page, request);
    for (const name of ["Bruno", "Chloé", "David", "Emma", "Fanny", "Gaël"]) {
      const dialog = await fillAdd(page, name, uniqueEmail(name));
      await dialog.getByRole("button", { name: "Add member" }).click();
      await expect(dialog).toBeHidden();
    }
    await page.reload();

    for (const name of ["Alice", "Bruno", "Chloé", "David", "Emma"]) {
      await expect(line(page, name)).toBeVisible();
    }
    await expect(line(page, "Fanny")).toBeHidden();
    await expect(line(page, "Gaël")).toBeHidden();

    await page.getByRole("button", { name: "Show all 7 members" }).click();

    await expect(line(page, "Fanny")).toBeVisible();
    await expect(line(page, "Gaël")).toBeVisible();
    await expect(page.getByText("Show all 7 members")).toBeHidden();
  });
});

test.describe("Add a member", () => {
  test("opens the dialog, with Role at Volunteer", async ({
    page,
    request,
  }) => {
    await openMembers(page, request);

    const dialog = await openAdd(page);

    await expect(
      dialog.getByLabel("Display name", { exact: true }),
    ).toBeVisible();
    await expect(dialog.getByLabel("Email", { exact: true })).toBeVisible();
    await expect(dialog.getByRole("combobox", { name: /^Role/ })).toHaveValue(
      "volunteer",
    );
    await expect(dialog.getByRole("button", { name: "Close" })).toBeVisible();
  });

  test("adding closes the dialog, says so and shows the member", async ({
    page,
    request,
  }) => {
    await openMembers(page, request);
    const email = uniqueEmail("Chloe");

    const dialog = await fillAdd(page, "Chloé", email);
    await dialog
      .getByRole("combobox", { name: /^Role/ })
      .selectOption({ label: "Manager" });
    await dialog.getByRole("button", { name: "Add member" }).click();

    await expect(dialog).toBeHidden();
    await expect(page.getByText("Chloé added.")).toBeVisible();
    await expect(line(page, email)).toContainText("not joined yet");
    await expect(line(page, email)).toContainText(/manager/i);
  });

  test("an existing member: the dialog stays open, with its message", async ({
    page,
    request,
  }) => {
    await openMembers(page, request);
    const email = uniqueEmail("Chloe");
    let dialog = await fillAdd(page, "Chloé", email);
    await dialog.getByRole("button", { name: "Add member" }).click();
    await expect(dialog).toBeHidden();

    dialog = await fillAdd(page, "Chloé", email);
    await dialog.getByRole("button", { name: "Add member" }).click();

    await expect(dialog.getByText("Chloé is already a member.")).toBeVisible();
    await expect(dialog).toBeVisible();
    await expect(dialog.getByLabel("Email", { exact: true })).toHaveValue(
      email,
    );
  });

  for (const way of ["Cancel", "the close button", "Escape"]) {
    test(`${way} closes it, changing nothing`, async ({ page, request }) => {
      await openMembers(page, request);
      const email = uniqueEmail("Chloe");
      const dialog = await fillAdd(page, "Chloé", email);

      if (way === "Cancel")
        await dialog.getByRole("button", { name: "Cancel" }).click();
      else if (way === "Escape") await page.keyboard.press("Escape");
      else await dialog.getByRole("button", { name: "Close" }).click();

      await expect(dialog).toBeHidden();
      await page.reload();
      await expect(page.locator("main")).not.toContainText(email);
    });
  }

  test("when the server fails: the generic error in the dialog, and what was typed stays", async ({
    page,
    request,
  }) => {
    const slug = await openMembers(page, request);
    await page.route(`**/association/${slug}/members`, (route) =>
      route.request().method() === "POST"
        ? route.fulfill({ status: 500, body: "failure" })
        : route.continue(),
    );

    const dialog = await fillAdd(page, "Chloé", "chloe@example.org");
    await dialog.getByRole("button", { name: "Add member" }).click();

    await expect(dialog.getByText(GENERIC)).toBeVisible();
    await expect(
      dialog.getByLabel("Display name", { exact: true }),
    ).toHaveValue("Chloé");
    await expect(dialog.getByLabel("Email", { exact: true })).toHaveValue(
      "chloe@example.org",
    );
  });
});
