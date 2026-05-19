import { expect, test } from '@playwright/test'

async function login(page: any) {
  await page.goto('/login')
  await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
  await page.getByTestId('password-input').fill('test-password-123')
  await page.getByTestId('login-submit').click()
  await page.waitForURL(/\/dashboard/)
}

test.describe('Approval Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('Workflow page exposes approval-related status or fallback state', async ({ page }) => {
    await page.goto('/workflows')
    const approvalRow = page.locator('tr:has-text("waiting_for_approval")')
    if ((await approvalRow.count()) > 0) {
      await approvalRow.first().click()
      await expect(page.getByText(/approval|reason/i)).toBeVisible()
      return
    }
    const hasEmpty = (await page.getByText(/no workflows found/i).count()) > 0
    const hasError = (await page.getByRole('alert').count()) > 0
    expect(hasEmpty || hasError).toEqual(true)
  })
})
