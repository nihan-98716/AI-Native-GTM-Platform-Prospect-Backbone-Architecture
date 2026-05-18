# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.ts >> keyboard navigation and accessible landmarks
- Location: tests\accessibility.spec.ts:3:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('main#main')
Expected: visible
Error: strict mode violation: locator('main#main') resolved to 2 elements:
    1) <main id="main" class="p-4 md:p-6">…</main> aka getByRole('main').filter({ hasText: 'ProspectDashboardAccountsWorkflowsIntegrations☰Workflow status: idle☀️' })
    2) <main id="main" class="p-4 md:p-6">…</main> aka getByRole('main').filter({ hasText: 'ProspectDashboardAccountsWorkflowsIntegrations☰Workflow status: idle☀️' }).locator('#main')

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('main#main')

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - link "Skip to main content" [ref=e2] [cursor=pointer]:
    - /url: "#main"
    - text: Skip to main
  - generic [ref=e3]:
    - complementary "Sidebar" [ref=e4]:
      - generic [ref=e6]: Prospect
      - navigation "Main navigation" [ref=e7]:
        - list [ref=e8]:
          - listitem [ref=e9]:
            - link "Dashboard" [ref=e10] [cursor=pointer]:
              - /url: /
          - listitem [ref=e11]:
            - link "Accounts" [ref=e12] [cursor=pointer]:
              - /url: /accounts
          - listitem [ref=e13]:
            - link "Workflows" [ref=e14] [cursor=pointer]:
              - /url: /workflows
          - listitem [ref=e15]:
            - link "Integrations" [ref=e16] [cursor=pointer]:
              - /url: /integrations
    - generic [ref=e17]:
      - banner [ref=e18]:
        - generic [ref=e20]:
          - text: "Workflow status:"
          - strong [ref=e21]: idle
        - generic [ref=e22]:
          - button "Toggle theme" [ref=e23] [cursor=pointer]: ☀️
          - generic [ref=e24]: User
      - main [ref=e25]:
        - generic [ref=e26]:
          - complementary "Sidebar" [ref=e27]:
            - generic [ref=e29]: Prospect
            - navigation "Main navigation" [ref=e30]:
              - list [ref=e31]:
                - listitem [ref=e32]:
                  - link "Dashboard" [ref=e33] [cursor=pointer]:
                    - /url: /
                - listitem [ref=e34]:
                  - link "Accounts" [ref=e35] [cursor=pointer]:
                    - /url: /accounts
                - listitem [ref=e36]:
                  - link "Workflows" [ref=e37] [cursor=pointer]:
                    - /url: /workflows
                - listitem [ref=e38]:
                  - link "Integrations" [ref=e39] [cursor=pointer]:
                    - /url: /integrations
          - generic [ref=e40]:
            - generic [ref=e41]:
              - generic [ref=e43]:
                - text: "Workflow status:"
                - strong [ref=e44]: idle
              - generic [ref=e45]:
                - button "Toggle theme" [ref=e46] [cursor=pointer]: ☀️
                - generic [ref=e47]: User
            - main [ref=e48]:
              - main [ref=e49]:
                - heading "Dashboard" [level=1] [ref=e50]
                - status [ref=e53]:
                  - img [ref=e54]
                - generic [ref=e57]:
                  - heading "Recent Activity" [level=2] [ref=e58]
                  - status [ref=e60]:
                    - img [ref=e61]
                - generic [ref=e64]:
                  - heading "Workflow Summary" [level=2] [ref=e65]
                  - status [ref=e67]:
                    - img [ref=e68]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test('keyboard navigation and accessible landmarks', async ({ page }) => {
  4  |   await page.goto('/')
  5  |   // Check landmark roles
  6  |   const main = page.locator('main#main')
> 7  |   await expect(main).toBeVisible()
     |                      ^ Error: expect(locator).toBeVisible() failed
  8  |   // Tab through header and open sidebar
  9  |   await page.keyboard.press('Tab')
  10 |   // basic assertion that page can be focused
  11 |   await expect(page).toHaveTitle(/Prospect UI/)
  12 | })
  13 | 
```