import { test } from '@playwright/test'

test('debug main count', async ({ page }) => {
  await page.goto('/')
  const mains = await page.evaluate(() => Array.from(document.querySelectorAll('main#main')).map(m => ({outer: m.outerHTML.slice(0, 200)})))
  console.log('MAINS=' + JSON.stringify(mains, null, 2))
})
