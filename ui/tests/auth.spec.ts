import { expect, test } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('Login with valid credentials grants access to dashboard', async ({ page }) => {
    await page.goto('/login')

    await expect(page.locator('form')).toBeVisible()
    await expect(page.getByTestId('email-input')).toBeVisible()
    await expect(page.getByTestId('password-input')).toBeVisible()

    await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
    await page.getByTestId('password-input').fill('test-password-123')
    await page.getByTestId('login-submit').click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByRole('heading', { level: 1, name: /dashboard/i })).toBeVisible()
  })

  test('Logout clears session and redirects to login', async ({ page }) => {
    await page.goto('/login')
    await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
    await page.getByTestId('password-input').fill('test-password-123')
    await page.getByTestId('login-submit').click()
    await page.waitForURL(/\/dashboard/)

    await page.goto('/dashboard')
    await expect(page.getByRole('button', { name: /logout/i })).toBeVisible()
    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('form')).toBeVisible()
  })

  test('Unauthenticated access redirects to login', async ({ page }) => {
    await page.goto('/workflows')
    await expect(page).toHaveURL(/\/login/)
  })

  test('Invalid JWT token is rejected', async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'auth_token',
        value: 'invalid.jwt.token',
        url: 'http://localhost:3000',
      },
    ])
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login|\/error/)
  })
})
