import { chromium } from "playwright";
import fetch from "node-fetch";
import fs from "fs";

const DISCORD_WEBHOOK = process.env.DISCORD_WEBHOOK!;

// Crear carpeta de screenshots si no existe
if (!fs.existsSync('screenshots')) fs.mkdirSync('screenshots');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // ====== LOGIN ======
    await page.goto('https://portal.cosem.com.uy/PortalWeb/uy.com.ust.hsglogin?,,');
    await page.screenshot({ path: 'screenshots/antes_login.png', fullPage: true });

    await page.getByRole('textbox', { name: 'Documento Documento' }).click();
    await page.getByRole('textbox', { name: 'Documento Documento' }).fill(process.env.USER_MUTUALISTA);

    await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).click();
    await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).fill(process.env.PASS_MUTUALISTA);
    await page.getByRole('textbox', { name: 'Contraseña Contraseña' }).press('Enter');

    // ====== IR A AGENDA ======
    await page.goto('https://portal.cosem.com.uy/PortalWeb/uy.com.ust.hmrodisdat');
    await page.screenshot({ path: 'screenshots/antes_agenda.png', fullPage: true });

    try {
      await page.getByRole('button', { name: 'Agenda' }).click();
    } catch (e) {
      await page.screenshot({ path: 'screenshots/fallo_agenda.png', fullPage: true });
      throw e;
    }

    await page.locator('#NUEVOTURNO i').click();

    // ====== BUSCAR ESPECIALIDAD ======
    const frame = await page.locator('#gxp0_ifrm').contentFrame();
    await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).click();
    await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).fill("dermatologia");
    await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).press("Enter");

    await frame.locator("div").filter({ hasText: /^DERMATOLOGIA$/ }).nth(3).click();

    await page.getByRole("button", { name: "Más tarde" }).click();

    // ====== CHEQUEO DE TURNOS ======
    const noHayHoras = await frame.locator("#span_vEMPTYNOHAYHORAS").isVisible().catch(() => false);

    await page.screenshot({ path: 'screenshots/resultado.png', fullPage: true });

    if (!noHayHoras) {
      await fetch(DISCORD_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "🚨 ¡Hay turnos disponibles en dermatología!",
        }),
      });
    }

  } catch (error) {
    // Captura general si algo falla
    await page.screenshot({ path: 'screenshots/error.png', fullPage: true });
    throw error;
  } finally {
    await browser.close();
  }
}

main();
