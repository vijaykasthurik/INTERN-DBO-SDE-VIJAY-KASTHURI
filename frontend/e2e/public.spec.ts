import { test, expect } from "@playwright/test";
for (const width of [375, 768, 1440]) {
  test(`public navigation, guards and contact at ${width}`, async ({page}) => {
    await page.setViewportSize({width, height:900});
    for (const [route, heading] of [["/", "Lumen"], ["/how-it-works", "How Lumen works"], ["/about", "Analysis with a visible evidence trail"], ["/contact", "Contact"]]) {
      await page.goto(route);
      await expect(page.getByRole("navigation", {name:"Public navigation"})).toBeVisible();
      await expect(page.getByRole("navigation", {name:"Main Navigation"})).toHaveCount(0);
      if(route !== "/") await expect(page.getByRole("heading", {name:heading, exact:true})).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth > innerWidth)).toBe(false);
    }
    await page.getByLabel("Name", {exact:true}).fill("Public Audit");
    await page.getByLabel("Email", {exact:true}).fill("audit@example.com");
    await page.getByLabel("Message", {exact:true}).fill("Checking the real contact intake.");
    if (width === 375) {
      await page.getByRole("button", {name:"Send message"}).click();
      await expect(page.getByRole("status")).toContainText("message was received");
    }
    await page.goto("/workspace");
    await expect(page).toHaveURL(/auth/);
    const email = `public_${width}_${Date.now()}@example.com`;
    await page.request.post("/api/v1/auth/register", {data:{email,password:"PublicPass123!",full_name:"Public Navigation"}});
    const login = await page.request.post("/api/v1/auth/login", {data:{email,password:"PublicPass123!"}});
    const token = (await login.json()).access_token as string;
    await page.addInitScript((value:string)=>localStorage.setItem("lumen_access_token",value),token);
    await page.goto("/about");
    await expect(page.getByRole("link", {name:"Go to workspace"})).toBeVisible();
    await expect(page.getByRole("navigation", {name:"Main Navigation"})).toHaveCount(0);
  });
}
