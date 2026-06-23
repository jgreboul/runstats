import { expect, test } from "@playwright/test";

test("dashboard loads seeded local data", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Training overview" }))
    .toBeVisible();
  await expect(page.getByText("Weekly distance")).toBeVisible();
  await expect(page.getByText("Sunday Long Run")).toBeVisible();
  await expect(page.getByText("Succeeded")).toBeVisible();
});

test("activity filters and detail route work against the API", async ({ page }) => {
  await page.goto("/activities");

  await expect(page.getByRole("link", { name: "Morning 5K" })).toBeVisible();
  await page.getByLabel("Search").fill("tempo");

  await expect(page.getByRole("link", { name: "Morning 5K" })).toBeHidden();
  await page.getByRole("link", { name: "Tempo 8K" }).click();

  await expect(page.getByRole("heading", { name: "Tempo 8K" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Laps" })).toBeVisible();
  await expect(page.getByText("8.04 km")).toBeVisible();
});

test("watch settings can pair, probe, save, and run fake sync", async ({ page }) => {
  await page.goto("/watch");

  await page.getByRole("button", { name: "Scan" }).click();
  await page.getByRole("button", { name: "Pair Garmin Forerunner 965" }).click();

  await expect(page.getByText("Garmin Forerunner 965", { exact: true }).first())
    .toBeVisible();
  await page.locator(".watch-stack select").first()
    .selectOption({ label: "Garmin Forerunner 965" });
  await page.getByRole("button", { name: "Probe capabilities" }).click();
  await expect(page.getByText(/direct activity export/i)).toBeVisible();

  await page.getByLabel("Import health stats").uncheck();
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.getByRole("region", { name: "Sync controls" }).getByText("Off"))
    .toBeVisible();

  await page.getByRole("button", { name: "Start sync" }).click();
  await expect(page.getByText("Sync succeeded")).toBeVisible();
  await expect(page.getByText("Sync completed successfully.")).toBeVisible();
});

test("chat answers include source references", async ({ page }) => {
  await page.goto("/chat");

  await expect(page.getByText("Seed training questions")).toBeVisible();
  await page.getByRole("textbox", { name: "Message" })
    .fill("Show my longest run with heart-rate details.");
  await page.getByRole("button", { name: "Send" }).click();

  const messages = page.getByLabel("Chat messages");
  await expect(messages.getByText(/Longest run: Sunday Long Run/i)).toBeVisible();
  await expect(messages.getByRole("link", { name: "Sunday Long Run" }))
    .toHaveAttribute("href", "/activities/seed-activity-003");
});

test("data management exports local data without deleting it", async ({ page }) => {
  await page.goto("/data-management");

  await page.getByLabel("Include raw archived files").check();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  const download = await downloadPromise;

  await expect(page.getByText("Export ready")).toBeVisible();
  await expect(page.locator(".data-management-summary").getByText("Activities"))
    .toBeVisible();
  await expect(page.locator(".data-management-summary").getByText("Health records"))
    .toBeVisible();
  expect(download.suggestedFilename()).toMatch(/^runstats-export-\d{4}-\d{2}-\d{2}\.json$/);
});
