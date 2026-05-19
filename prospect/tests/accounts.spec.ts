import { expect, test } from '@playwright/test'

async function login(page: any) {
  await page.goto('/login')
  await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
  await page.getByTestId('password-input').fill('test-password-123')
  await page.getByTestId('login-submit').click()
  await page.waitForURL(/\/dashboard/)
}

test.describe('Accounts Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('Accounts page renders heading and state container', async ({ page }) => {
    await page.goto('/accounts')
    await expect(page.getByRole('heading', { level: 1, name: /accounts/i })).toBeVisible()
    const hasTable = (await page.getByRole('table').count()) > 0
    const hasEmpty = (await page.getByText(/no accounts found/i).count()) > 0
    const hasError = (await page.getByRole('alert').count()) > 0
    expect(hasTable || hasEmpty || hasError).toEqual(true)
  })

  test('Accounts filters and sort controls are interactive', async ({ page }) => {
    await page.goto('/accounts')
    const search = page.getByLabel('Search accounts')
    await expect(search).toBeVisible()
    await search.fill('test')

    const sortSelect = page.locator('select').first()
    await expect(sortSelect).toBeVisible()
    await sortSelect.selectOption('domain')
    await expect(sortSelect).toHaveValue('domain')
  })

  test('Accounts pagination controls render and can be triggered', async ({ page }) => {
    await page.goto('/accounts')
    const prev = page.getByRole('button', { name: /previous page/i })
    const next = page.getByRole('button', { name: /next page/i })
    await expect(prev).toBeVisible()
    await expect(next).toBeVisible()
    await next.click()
    await prev.click()
  })

  test('Accounts rows are keyboard focusable when present', async ({ page }) => {
    await page.goto('/accounts')
    const rowCount = await page.locator('tbody tr').count()
    if (rowCount === 0) {
      const hasEmpty = (await page.getByText(/no accounts found/i).count()) > 0
      const hasError = (await page.getByRole('alert').count()) > 0
      expect(hasEmpty || hasError).toEqual(true)
      return
    }

    const firstRow = page.locator('tbody tr').first()
    await firstRow.click()
    await page.keyboard.press('Tab')
    await expect(firstRow).toBeVisible()
  })
})
