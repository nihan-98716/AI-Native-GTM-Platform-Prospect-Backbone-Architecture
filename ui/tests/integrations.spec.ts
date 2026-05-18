import { expect, test } from '@playwright/test'

async function login(page: any) {
  await page.goto('/login')
  await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
  await page.getByTestId('password-input').fill('test-password-123')
  await page.getByTestId('login-submit').click()
  await page.waitForURL(/\/dashboard/)
}

test.describe('Integration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('Integrations page lists provider cards', async ({ page }) => {
    await page.goto('/settings/integrations')
    await expect(page.getByRole('heading', { level: 1, name: /integrations/i })).toBeVisible()
    const cards = page.locator('[data-testid="provider-card"]')
    const cardCount = await cards.count()
    expect(cardCount).toBeGreaterThan(0)
  })

  test('Provider card displays status badge with supported state text', async ({ page }) => {
    await page.goto('/settings/integrations')
    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    await expect(apolloCard).toBeVisible()

    const statusText = ((await apolloCard.locator('[data-testid="status-badge"]').textContent()) ?? '').trim()
    expect(statusText).toMatch(/Connected|Disconnected|Failed|Live|Not configured|Rate limited/i)
  })

  test('Connected integrations show health section', async ({ page }) => {
    await page.goto('/settings/integrations')
    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    await expect(apolloCard).toBeVisible()
    await expect(apolloCard.locator('[data-testid="health-status"]')).toBeVisible()
  })

  test('Provider card shows last sync metadata', async ({ page }) => {
    await page.goto('/settings/integrations')
    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    await expect(apolloCard).toBeVisible()
    const syncValue = ((await apolloCard.locator('[data-testid="last-sync"]').textContent()) ?? '').trim()
    expect(syncValue.length).toBeGreaterThan(0)
    expect(syncValue).not.toMatch(/^Unavailable$/i)
  })
})
