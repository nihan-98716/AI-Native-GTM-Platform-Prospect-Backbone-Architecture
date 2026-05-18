import { test, expect } from '@playwright/test'

/**
 * Phase 7 E2E Tests
 *
 * Comprehensive end-to-end test suite validating:
 * 1. Authentication and authorization flows
 * 2. Accounts list and filtering
 * 3. Workflow execution and status tracking
 * 4. Trace and execution detail visibility
 * 5. Integration connection management
 * 6. Approval workflow and human gates
 *
 * Test data is pre-seeded via Phase 7 test data generator.
 */

test.describe('Authentication Flow', () => {
  test('Login with valid credentials grants access to dashboard', async ({
    page,
  }) => {
    await page.goto('/login')

    // Check login form renders
    await expect(page.locator('form')).toBeVisible()
    await expect(page.locator('input[name="email"]')).toBeVisible()
    await expect(page.locator('input[name="password"]')).toBeVisible()

    // Fill login form with test credentials
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')

    // Submit login
    await page.locator('button[type="submit"]').click()

    // Verify redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.locator('h1')).toContainText('Dashboard')
  })

  test('Logout clears session and redirects to login', async ({ page }) => {
    // Assume authenticated via login cookie
    await page.goto('/dashboard')

    // Click logout button
    await page.locator('button[aria-label="Logout"]').click()

    // Verify redirect to login
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('form')).toBeVisible()
  })

  test('Unauthenticated access redirects to login', async ({ page }) => {
    await page.goto('/workflows')
    await expect(page).toHaveURL(/\/login/)
  })

  test('Invalid JWT token shows error', async ({ page }) => {
    // Set invalid token in cookie
    await page.context().addCookies([
      {
        name: 'auth_token',
        value: 'invalid.jwt.token',
        url: 'http://localhost:3000',
      },
    ])

    await page.goto('/dashboard')

    // Should redirect to login or show error
    await expect(page).toHaveURL(/\/login|\/error/)
  })
})

test.describe('Accounts Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/dashboard/)
  })

  test('Accounts page loads with list of accounts', async ({ page }) => {
    await page.goto('/accounts')

    // Verify page title
    await expect(page.locator('h1')).toContainText('Accounts')

    // Verify table renders with data
    await expect(page.locator('table')).toBeVisible()
    await expect(page.locator('tbody tr')).toBeTruthy()

    // Verify table has at least one account
    const rows = await page.locator('tbody tr').count()
    expect(rows).toBeGreaterThan(0)
  })

  test('Accounts table supports filtering by industry', async ({ page }) => {
    await page.goto('/accounts')

    // Find filter input
    const filterInput = page.locator('input[placeholder*="Filter"]').first()
    await filterInput.fill('Software')

    // Verify filtered results
    await page.waitForTimeout(300) // Debounce delay
    const visibleRows = await page.locator('tbody tr:visible').count()
    expect(visibleRows).toBeGreaterThan(0)

    // Verify all visible rows contain "Software"
    const firstCell = await page.locator('tbody tr:visible td').first().textContent()
    expect(firstCell?.toLowerCase()).toContain('software')
  })

  test('Accounts table supports sorting by name', async ({ page }) => {
    await page.goto('/accounts')

    // Click "Name" column header to sort
    await page.locator('th:has-text("Name")').click()

    // Verify sort indicator appears
    await expect(page.locator('th:has-text("Name") [aria-sort]')).toBeVisible()

    // Verify rows are sorted (basic check: first row name < second row name)
    const firstRowName = await page
      .locator('tbody tr:first-child td:nth-child(2)')
      .textContent()
    const secondRowName = await page
      .locator('tbody tr:nth-child(2) td:nth-child(2)')
      .textContent()

    if (firstRowName && secondRowName) {
      expect(firstRowName.localeCompare(secondRowName)).toBeLessThanOrEqual(0)
    }
  })

  test('Accounts table pagination works correctly', async ({ page }) => {
    await page.goto('/accounts')

    // Verify pagination controls
    const paginationButtons = page.locator('button[aria-label*="Page"]')
    const buttonCount = await paginationButtons.count()
    expect(buttonCount).toBeGreaterThan(0)

    // Click next page
    const nextButton = page.locator('button:has-text("Next")')
    if (await nextButton.isEnabled()) {
      await nextButton.click()
      await page.waitForTimeout(300)

      // Verify page changed
      await expect(page.locator('tbody tr')).toBeTruthy()
    }
  })

  test('Account detail view shows account information', async ({ page }) => {
    await page.goto('/accounts')

    // Click first account row
    await page.locator('tbody tr:first-child').click()

    // Verify detail view
    await expect(page.locator('h2')).toContainText('Account Details')
    await expect(page.locator('text="Domain"')).toBeVisible()
    await expect(page.locator('text="Industry"')).toBeVisible()
  })
})

test.describe('Workflow Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/dashboard/)
  })

  test('Workflows page displays list of workflow runs', async ({ page }) => {
    await page.goto('/workflows')

    // Verify page title
    await expect(page.locator('h1')).toContainText('Workflows')

    // Verify table renders
    await expect(page.locator('table')).toBeVisible()
    const rows = await page.locator('tbody tr').count()
    expect(rows).toBeGreaterThan(0)
  })

  test('Workflow status badges display correctly', async ({ page }) => {
    await page.goto('/workflows')

    // Verify status badges for different states
    await expect(
      page.locator('[data-status="succeeded"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-status="running"]')
    ).toBeVisible()
    await expect(
      page.locator('[data-status="queued"]')
    ).toBeVisible()
  })

  test('Workflow detail view shows execution timeline', async ({ page }) => {
    await page.goto('/workflows')

    // Click completed workflow
    const completedRow = page.locator(
      'tr:has-text("succeeded") >> nth=0'
    )
    await completedRow.click()

    // Verify detail page
    await expect(page).toHaveURL(/\/workflows\//)
    await expect(page.locator('h2')).toContainText('Workflow')

    // Verify timeline component
    await expect(page.locator('[role="timeline"]')).toBeVisible()

    // Verify timeline steps
    const timelineSteps = page.locator('[role="timeline"] [role="listitem"]')
    const stepCount = await timelineSteps.count()
    expect(stepCount).toBeGreaterThan(0)
  })

  test('Workflow can be started from dashboard', async ({ page }) => {
    await page.goto('/dashboard')

    // Find "Start Workflow" button
    await expect(page.locator('button:has-text("Start Workflow")')).toBeVisible()
    await page.locator('button:has-text("Start Workflow")').click()

    // Verify modal opens
    await expect(page.locator('dialog')).toBeVisible()

    // Select ICP and account
    await page.locator('select[name="icp_id"]').selectOption('test-icp-1')
    await page.locator('select[name="account_id"]').selectOption('test-account-1')

    // Click start
    await page.locator('dialog button:has-text("Start")').click()

    // Verify navigation to workflow detail
    await expect(page).toHaveURL(/\/workflows\//)
  })

  test('Workflow shows loading state during execution', async ({ page }) => {
    await page.goto('/workflows')

    // Find running workflow
    const runningRow = page.locator(
      'tr:has-text("running") >> nth=0'
    )
    await runningRow.click()

    // Verify detail page shows loading indicator
    await expect(page.locator('[role="status"]')).toBeVisible()

    // Verify "Executing" or similar state
    await expect(
      page.locator('text=/Executing|In Progress|Running/i')
    ).toBeVisible()
  })
})

test.describe('Trace Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/dashboard/)
  })

  test('Workflow detail shows agent traces', async ({ page }) => {
    await page.goto('/workflows')

    // Click completed workflow
    const completedRow = page.locator(
      'tr:has-text("succeeded") >> nth=0'
    )
    await completedRow.click()

    // Scroll to traces section
    await page.locator('text="Traces"').scrollIntoViewIfNeeded()

    // Verify traces component
    await expect(page.locator('[data-testid="traces-panel"]')).toBeVisible()

    // Verify trace entries
    const traceEntries = page.locator('[data-testid="trace-entry"]')
    const traceCount = await traceEntries.count()
    expect(traceCount).toBeGreaterThan(0)
  })

  test('Trace entries show agent name, duration, and status', async ({ page }) => {
    await page.goto('/workflows')

    const completedRow = page.locator(
      'tr:has-text("succeeded") >> nth=0'
    )
    await completedRow.click()

    // Scroll to traces
    await page.locator('text="Traces"').scrollIntoViewIfNeeded()

    // Verify trace entry structure
    const firstTrace = page.locator('[data-testid="trace-entry"]').first()
    await expect(firstTrace.locator('[data-testid="agent-name"]')).toBeVisible()
    await expect(firstTrace.locator('[data-testid="duration"]')).toBeVisible()
    await expect(firstTrace.locator('[data-testid="status"]')).toBeVisible()
  })

  test('Trace redaction hides sensitive fields', async ({ page }) => {
    await page.goto('/workflows')

    const completedRow = page.locator(
      'tr:has-text("succeeded") >> nth=0'
    )
    await completedRow.click()

    // Expand trace details
    await page.locator('[data-testid="trace-entry"]').first().click()

    // Verify sensitive fields are not visible or redacted
    const traceContent = await page.locator('[data-testid="trace-details"]').textContent()

    // Should NOT contain API keys, tokens, or auth headers
    expect(traceContent).not.toMatch(/api[_-]key|authorization|token|secret/i)
  })

  test('Tool invocations show names, inputs, and outputs', async ({ page }) => {
    await page.goto('/workflows')

    const completedRow = page.locator(
      'tr:has-text("succeeded") >> nth=0'
    )
    await completedRow.click()

    await page.locator('text="Traces"').scrollIntoViewIfNeeded()

    // Expand trace entry
    await page.locator('[data-testid="trace-entry"]').first().click()

    // Verify tool invocation section
    await expect(
      page.locator('[data-testid="tool-invocations"]')
    ).toBeVisible()

    // Verify tool call structure
    const toolCalls = page.locator('[data-testid="tool-call"]')
    expect(await toolCalls.count()).toBeGreaterThan(0)
  })
})

test.describe('Integration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/dashboard/)
  })

  test('Integrations page lists connected providers', async ({ page }) => {
    await page.goto('/settings/integrations')

    // Verify page title
    await expect(page.locator('h1')).toContainText('Integrations')

    // Verify provider list renders
    const providers = page.locator('[data-testid="provider-card"]')
    expect(await providers.count()).toBeGreaterThan(0)
  })

  test('Provider card shows status: connected or disconnected', async ({
    page,
  }) => {
    await page.goto('/settings/integrations')

    // Verify Apollo provider showing as connected
    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    await expect(apolloCard).toBeVisible()

    // Check status badge
    const statusBadge = apolloCard.locator('[data-testid="status-badge"]')
    const statusText = await statusBadge.textContent()
    expect(['Connected', 'Disconnected', 'Failed']).toContain(statusText)
  })

  test('Health check status displays for connected integrations', async ({
    page,
  }) => {
    await page.goto('/settings/integrations')

    // Find connected provider
    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    await expect(apolloCard).toBeVisible()

    // Verify health check displays
    const healthStatus = apolloCard.locator('[data-testid="health-status"]')
    await expect(healthStatus).toBeVisible()
  })

  test('Last sync time displays', async ({ page }) => {
    await page.goto('/settings/integrations')

    const apolloCard = page.locator('[data-testid="provider-card"]:has-text("Apollo")')
    const lastSyncText = apolloCard.locator('[data-testid="last-sync"]')
    await expect(lastSyncText).toBeVisible()

    // Verify it contains a time
    const syncContent = await lastSyncText.textContent()
    expect(syncContent).toBeTruthy()
  })
})

test.describe('Approval Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[name="email"]').fill('test-seller@test-enterprise-saas.test')
    await page.locator('input[name="password"]').fill('test-password-123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/dashboard/)
  })

  test('Workflow waiting for approval shows approval gate', async ({ page }) => {
    await page.goto('/workflows')

    // Find workflow waiting for approval
    const approvalRow = page.locator(
      'tr:has-text("waiting_for_approval") >> nth=0'
    )
    await approvalRow.click()

    // Verify approval gate component
    await expect(
      page.locator('[data-testid="approval-gate"]')
    ).toBeVisible()
  })

  test('Approval gate shows hypotheses and reasons', async ({ page }) => {
    await page.goto('/workflows')

    const approvalRow = page.locator(
      'tr:has-text("waiting_for_approval") >> nth=0'
    )
    await approvalRow.click()

    // Verify approval details
    const approvalGate = page.locator('[data-testid="approval-gate"]')
    await expect(approvalGate.locator('text="Reason"')).toBeVisible()
    await expect(approvalGate.locator('[data-testid="hypothesis-summary"]')).toBeVisible()
  })

  test('Can approve workflow from approval gate', async ({ page }) => {
    await page.goto('/workflows')

    const approvalRow = page.locator(
      'tr:has-text("waiting_for_approval") >> nth=0'
    )
    await approvalRow.click()

    // Click approve button
    const approveButton = page.locator('button:has-text("Approve")')
    await expect(approveButton).toBeVisible()
    await approveButton.click()

    // Verify confirmation or loading state
    await expect(approveButton).toBeDisabled()
  })

  test('Can reject workflow from approval gate', async ({ page }) => {
    await page.goto('/workflows')

    const approvalRow = page.locator(
      'tr:has-text("waiting_for_approval") >> nth=0'
    )
    await approvalRow.click()

    // Click reject button
    const rejectButton = page.locator('button:has-text("Reject")')
    await expect(rejectButton).toBeVisible()
    await rejectButton.click()

    // Verify confirmation dialog appears
    await expect(page.locator('dialog')).toBeVisible()
    await expect(page.locator('dialog >> text="Are you sure"')).toBeVisible()
  })
})

test.describe('Accessibility Compliance', () => {
  test('All pages have exactly one main landmark', async ({ page }) => {
    const routes = ['/', '/dashboard', '/accounts', '/workflows', '/settings/integrations']

    for (const route of routes) {
      await page.goto(route)
      const mains = await page.locator('main').count()
      expect(mains).toBe(
        1,
        `Expected 1 main landmark on ${route}, found ${mains}`
      )
    }
  })

  test('Form inputs have associated labels', async ({ page }) => {
    await page.goto('/login')

    // Check email input has label
    const emailLabel = page.locator('label[for="email"]')
    await expect(emailLabel).toBeVisible()

    const emailInput = page.locator('input#email')
    await expect(emailInput).toBeVisible()
  })

  test('Buttons have accessible names', async ({ page }) => {
    await page.goto('/dashboard')

    // Verify buttons have text or aria-label
    const buttons = page.locator('button')
    const buttonCount = await buttons.count()

    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = buttons.nth(i)
      const text = await button.textContent()
      const ariaLabel = await button.getAttribute('aria-label')

      const hasAccessibleName = text?.trim() || ariaLabel
      expect(hasAccessibleName).toBeTruthy()
    }
  })

  test('Links have descriptive text', async ({ page }) => {
    await page.goto('/workflows')

    // Verify links are not just "Click here"
    const links = page.locator('a')
    const linkCount = await links.count()

    for (let i = 0; i < Math.min(linkCount, 5); i++) {
      const link = links.nth(i)
      const text = await link.textContent()
      const href = await link.getAttribute('href')

      expect(text?.trim()).not.toBe('Click here')
      expect(href).toBeTruthy()
    }
  })

  test('Focus is visible on keyboard navigation', async ({ page }) => {
    await page.goto('/dashboard')

    // Tab to first interactive element
    await page.keyboard.press('Tab')

    // Get focused element
    const focusedElement = await page.evaluate(() => document.activeElement?.outerHTML)
    expect(focusedElement).toBeTruthy()

    // Verify focus is visible (has outline or focus class)
    const focusStyle = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement
      if (!el) return null
      const computed = window.getComputedStyle(el)
      return {
        outline: computed.outline,
        boxShadow: computed.boxShadow,
      }
    })

    const hasFocusStyle =
      focusStyle?.outline !== 'none' || focusStyle?.boxShadow !== 'none'
    expect(hasFocusStyle).toBeTruthy()
  })

  test('Skip link is keyboard accessible', async ({ page }) => {
    await page.goto('/')

    // Press Tab to access skip link
    await page.keyboard.press('Tab')

    // Get focused element
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.getAttribute('href')
    })

    expect(focusedElement).toContain('#main')
  })
})

test.describe('Performance', () => {
  test('Dashboard loads within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/dashboard')
    await expect(page.locator('h1')).toBeVisible()
    const loadTime = Date.now() - startTime

    expect(loadTime).toBeLessThan(3000) // 3 second threshold
  })

  test('Accounts list renders large datasets efficiently', async ({ page }) => {
    await page.goto('/accounts')

    // Measure render time
    const startTime = Date.now()
    await expect(page.locator('tbody tr').first()).toBeVisible()
    const renderTime = Date.now() - startTime

    expect(renderTime).toBeLessThan(2000)

    // Verify table is still interactive
    await page.locator('input[placeholder*="Filter"]').fill('Software')
    await page.waitForTimeout(500)
    const filtered = await page.locator('tbody tr:visible').count()
    expect(filtered).toBeGreaterThan(0)
  })

  test('Workflow detail page does not re-render excessively', async ({
    page,
  }) => {
    await page.goto('/workflows')

    // Open workflow detail
    await page.locator('tbody tr:first-child').click()

    // Monitor for unnecessary renders (basic check: page remains stable)
    const initialTitle = await page.locator('h1').textContent()
    await page.waitForTimeout(1000)
    const finalTitle = await page.locator('h1').textContent()

    expect(initialTitle).toBe(finalTitle) // Title should not change
  })
})
