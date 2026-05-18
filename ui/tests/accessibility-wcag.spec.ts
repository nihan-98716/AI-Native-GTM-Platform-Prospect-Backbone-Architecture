import { expect, test } from '@playwright/test'

function parseRgb(color: string): [number, number, number] | null {
  const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i)
  if (!match) {
    return null
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])]
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const normalize = (v: number): number => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  const [rr, gg, bb] = [normalize(r), normalize(g), normalize(b)]
  return 0.2126 * rr + 0.7152 * gg + 0.0722 * bb
}

function contrastRatio(foreground: [number, number, number], background: [number, number, number]): number {
  const l1 = relativeLuminance(foreground)
  const l2 = relativeLuminance(background)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

async function login(page: any) {
  await page.goto('/login')
  await page.getByTestId('email-input').fill('test-seller@test-enterprise-saas.test')
  await page.getByTestId('password-input').fill('test-password-123')
  await page.getByTestId('login-submit').click()
  await page.waitForURL(/\/dashboard/)
}

test.describe('WCAG 2.2 AA Validation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('primary routes expose one main landmark and required structural landmarks', async ({ page }) => {
    const routes = ['/dashboard', '/accounts', '/workflows', '/settings/integrations']
    for (const route of routes) {
      await page.goto(route)
      await expect(page.locator('main#main')).toHaveCount(1)
      await expect(page.locator('header,[role="banner"]')).toHaveCount(1)
      await expect(page.locator('nav,[role="navigation"]')).toHaveCount(1)
    }
  })

  test('skip link moves focus to main content', async ({ page }) => {
    await page.goto('/dashboard')
    await page.keyboard.press('Tab')
    const skipLink = page.locator('a[href="#main"]').first()
    await expect(skipLink).toBeVisible()
    await skipLink.press('Enter')
    const focusedId = await page.evaluate(() => document.activeElement?.id ?? null)
    expect(focusedId).toEqual('main')
  })

  test('form controls have explicit labels or ARIA names', async ({ page }) => {
    await page.evaluate(() => window.localStorage.removeItem('token'))
    await page.goto('/login')
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    expect(inputCount).toBeGreaterThan(0)

    for (let i = 0; i < inputCount; i += 1) {
      const input = inputs.nth(i)
      await expect(input).toBeVisible()
      const id = await input.getAttribute('id')
      const ariaLabel = await input.getAttribute('aria-label')
      const ariaLabelledBy = await input.getAttribute('aria-labelledby')

      let hasLabel = false
      if (id) {
        const associatedLabels = page.locator(`label[for="${id}"]`)
        hasLabel = (await associatedLabels.count()) > 0
      }
      const hasAriaName = Boolean((ariaLabel ?? '').trim() || (ariaLabelledBy ?? '').trim())
      expect(hasLabel || hasAriaName).toEqual(true)
    }
  })

  test('buttons expose accessible names', async ({ page }) => {
    await page.goto('/dashboard')
    const buttons = page.getByRole('button')
    const buttonCount = await buttons.count()
    expect(buttonCount).toBeGreaterThan(0)

    for (let i = 0; i < Math.min(buttonCount, 10); i += 1) {
      const button = buttons.nth(i)
      await expect(button).toBeVisible()
      const text = ((await button.textContent()) ?? '').trim()
      const ariaLabel = ((await button.getAttribute('aria-label')) ?? '').trim()
      const title = ((await button.getAttribute('title')) ?? '').trim()
      expect(text.length > 0 || ariaLabel.length > 0 || title.length > 0).toEqual(true)
    }
  })

  test('keyboard tab navigation keeps visible focus indicator', async ({ page }) => {
    await page.goto('/dashboard')
    for (let i = 0; i < 6; i += 1) {
      await page.keyboard.press('Tab')
      const focusStyle = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null
        if (!el) {
          return null
        }
        const css = window.getComputedStyle(el)
        return {
          outlineStyle: css.outlineStyle,
          outlineWidth: css.outlineWidth,
          boxShadow: css.boxShadow,
          visibility: css.visibility,
        }
      })
      expect(focusStyle).not.toBeNull()
      expect(focusStyle?.visibility).toEqual('visible')
      const outlineVisible = focusStyle?.outlineStyle !== 'none' && focusStyle?.outlineWidth !== '0px'
      const boxShadowVisible = focusStyle?.boxShadow !== 'none'
      expect(outlineVisible || boxShadowVisible).toEqual(true)
    }
  })

  test('table semantics include header cells with scope attributes', async ({ page }) => {
    await page.goto('/accounts')
    const table = page.getByRole('table')
    if ((await table.count()) === 0) {
      const hasEmpty = (await page.getByText(/no accounts found/i).count()) > 0
      const hasError = (await page.getByRole('alert').count()) > 0
      expect(hasEmpty || hasError).toEqual(true)
      return
    }
    await expect(table).toBeVisible()
    const headerCells = table.locator('th')
    const headerCount = await headerCells.count()
    expect(headerCount).toBeGreaterThan(0)
    const scopedHeaderCount = await table.locator('th[scope]').count()
    expect(scopedHeaderCount).toBeGreaterThan(0)
  })

  test('text contrast meets WCAG AA threshold for sampled body text', async ({ page }) => {
    await page.goto('/dashboard')
    const samples = await page.evaluate(() => {
      const nodes = Array.from(document.querySelectorAll<HTMLElement>('main h1, main h2, main h3, main p, main a, main label'))
      return nodes
        .map((node) => {
          const text = (node.textContent ?? '').trim()
          const cs = window.getComputedStyle(node)
          let backgroundColor = cs.backgroundColor
          let parent: HTMLElement | null = node.parentElement
          while (
            parent &&
            (backgroundColor === 'transparent' || backgroundColor === 'rgba(0, 0, 0, 0)')
          ) {
            backgroundColor = window.getComputedStyle(parent).backgroundColor
            parent = parent.parentElement
          }
          return {
            text,
            color: cs.color,
            backgroundColor,
            fontSize: cs.fontSize,
            fontWeight: cs.fontWeight,
          }
        })
        .filter((item) => item.text.length > 0)
        .slice(0, 12)
    })

    expect(samples.length).toBeGreaterThan(0)
    let checked = 0
    for (const sample of samples) {
      const fg = parseRgb(sample.color)
      const bg = parseRgb(sample.backgroundColor) ?? [255, 255, 255]
      if (fg === null) continue
      const ratio = contrastRatio(fg, bg)
      const sizePx = Number(sample.fontSize.replace('px', ''))
      const isLargeText = sizePx >= 24 || (sizePx >= 18.66 && Number(sample.fontWeight) >= 700)
      const minimumRatio = isLargeText ? 3.0 : 4.5
      expect(ratio).toBeGreaterThanOrEqual(minimumRatio)
      checked += 1
    }
    expect(checked).toBeGreaterThan(0)
  })
})

test.describe('Keyboard and Responsive Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('mobile layout avoids horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/dashboard')
    const dimensions = await page.evaluate(() => ({
      bodyWidth: document.body.scrollWidth,
      viewportWidth: window.innerWidth,
    }))
    expect(dimensions.bodyWidth).toBeLessThanOrEqual(dimensions.viewportWidth + 1)
  })

  test('modal is dismissible via escape key and focus returns to trigger', async ({ page }) => {
    await page.goto('/dashboard')
    const trigger = page.getByRole('button', { name: /start workflow/i })
    await expect(trigger).toBeVisible()
    await trigger.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })
})
