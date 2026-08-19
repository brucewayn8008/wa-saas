import { expect, test } from "@playwright/test";

test("dashboard → conversations → listening feed", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({
    timeout: 15_000,
  });

  await page.getByRole("link", { name: "Conversations" }).first().click();
  await expect(page.getByRole("heading", { name: "Conversations" })).toBeVisible();
  await expect(page.getByText("Priya Sharma").first()).toBeVisible();

  await page.getByRole("link", { name: "Listening" }).first().click();
  await expect(page.getByRole("heading", { name: "Listening" })).toBeVisible();
  await expect(
    page.getByText(/automatically replies to the lead/i).first()
  ).toBeVisible();
  // Live API may be empty in CI — assert feed chrome, not mock cards.
  await expect(page.getByRole("button", { name: /Approve/i })).toHaveCount(0);
});
