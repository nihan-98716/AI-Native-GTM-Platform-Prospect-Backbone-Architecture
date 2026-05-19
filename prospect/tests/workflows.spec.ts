import { expect, test } from '@playwright/test'

async function login(page: any) {
  await page.goto('/login')
  await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
  await page.getByTestId('password-input').fill('test-password-123')
  await page.getByTestId('login-submit').click()
  await page.waitForURL(/\/dashboard/)
}

test.describe('Workflow Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('Workflows page renders list container or empty/error state', async ({ page }) => {
    await page.goto('/workflows')
    await expect(page.getByRole('heading', { level: 1, name: /workflows/i })).toBeVisible()
    const hasTable = (await page.getByRole('table').count()) > 0
    const hasEmpty = (await page.getByText(/no workflows found/i).count()) > 0
    const hasError = (await page.getByRole('alert').count()) > 0
    expect(hasTable || hasEmpty || hasError).toEqual(true)
  })

  test('Workflow start flow opens dialog and navigates to detail', async ({ page }) => {
    await page.goto('/dashboard')
    const startButton = page.getByRole('button', { name: /start workflow/i })
    await expect(startButton).toBeVisible()
    await startButton.click()

    const dialog = page.getByRole('dialog', { name: /start workflow/i })
    await expect(dialog).toBeVisible()
    await dialog.locator('select[name="icp_id"]').selectOption('test-icp-1')
    await dialog.locator('select[name="account_id"]').selectOption('test-account-1')
    await dialog.getByRole('button', { name: /^start$/i }).click()
    await expect(page).toHaveURL(/\/workflows\//)
  })
})

test.describe('Trace Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('Workflow detail route renders with timeline/traces or fallback', async ({ page }) => {
    await page.goto('/workflows/test-icp-1-test-account-1')
    const hasTimeline = (await page.getByText(/timeline/i).count()) > 0
    const hasTraces = (await page.getByText(/agent traces|no tool calls/i).count()) > 0
    const hasError = (await page.getByRole('alert').count()) > 0
    expect(hasTimeline || hasTraces || hasError).toEqual(true)
  })
})
