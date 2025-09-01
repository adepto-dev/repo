import { chromium } from "playwright";
import fetch from "node-fetch";

const DISCORD_WEBHOOK = process.env.DISCORD_WEBHOOK!;

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://portal.cosem.com.uy/PortalWeb/uy.com.ust.hsglogin?,,');
  await page.getByRole('textbox', { name: 'Documento Documento' }).click();
  await page.getByRole('textbox', { name: 'Documento Documento' }).fill(process.env.USER_MUTUALISTA);
  await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).click();
  await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).fill(process.env.PASS_MUTUALISTA);
  await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).press('Enter');
  await page.goto('https://portal.cosem.com.uy/PortalWeb/uy.com.ust.hmrodisdat');
  await page.screenshot({ path: 'antes_agenda.png', fullPage: true });
  await page.getByRole('button', { name: 'Agenda' }).click();
  await page.locator('#NUEVOTURNO i').click();
  await page.locator('#gxp0_ifrm').contentFrame().getByRole('textbox', { name: 'Buscar especialidad o' }).click();
  await page
    .locator("#gxp0_ifrm")
    .contentFrame()
    .getByRole("textbox", { name: "Buscar especialidad o" })
    .fill("dermatologia");

  await page
    .locator("#gxp0_ifrm")
    .contentFrame()
    .getByRole("textbox", { name: "Buscar especialidad o" })
    .press("Enter");

  await page
    .locator("#gxp0_ifrm")
    .contentFrame()
    .locator("div")
    .filter({ hasText: /^DERMATOLOGIA$/ })
    .nth(3)
    .click();

  await page.getByRole("button", { name: "Más tarde" }).click();

  // ========== CHEQUEO DE TURNOS ==========
  const noHayHoras = await page
    .locator("#gxp0_ifrm")
    .contentFrame()
    .locator("#span_vEMPTYNOHAYHORAS")
    .isVisible()
    .catch(() => false);

  if (!noHayHoras) {
    await fetch(DISCORD_WEBHOOK, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: "🚨 ¡Hay turnos disponibles en dermatología!",
      }),
    });
  }

  await browser.close();
}

main();
