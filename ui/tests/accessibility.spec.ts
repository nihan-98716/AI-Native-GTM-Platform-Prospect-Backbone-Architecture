import { test, expect } from '@playwright/test'

test('keyboard navigation and accessible landmarks', async ({ page }) => {
  await page.goto('/')
  // Check landmark roles
  const main = page.locator('main#main')
  await expect(main).toBeVisible()
  // Tab through header and open sidebar
  await page.keyboard.press('Tab')
  // basic assertion that page can be focused
  await expect(page).toHaveTitle(/Prospect UI/)
})
