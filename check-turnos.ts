import { chromium } from "playwright";
import fetch from "node-fetch";
import fs from "fs";

const DISCORD_WEBHOOK = process.env.DISCORD_WEBHOOK_URL!;

// Crear carpeta de screenshots si no existe
if (!fs.existsSync('screenshots')) fs.mkdirSync('screenshots');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // ====== LOGIN ======
    await page.goto('https://portal.cosem.com.uy/PortalWeb/uy.com.ust.hsglogin?,,');
    await page.screenshot({ path: 'screenshots/antes_login.png', fullPage: true });
    const user = process.env.USER_MUTUALISTA!;
    const pass = process.env.PASS_MUTUALISTA!;
    try {
      // Input Usuario
      const usuarioInput = page.locator('#vUSUARIO');
      await usuarioInput.waitFor({ state: 'visible', timeout: 30000 });
      await usuarioInput.fill(user);
  
      // Input Contraseña
      const passwordInput = page.locator('#vPASSWORD');
      await passwordInput.waitFor({ state: 'visible', timeout: 30000 });
      await passwordInput.fill(pass);
  
      // Botón Login (buscar cualquier texto descendiente que diga "Ingresar")
      const loginBtn = page.locator('button:has-text("Entrar")');
      await loginBtn.waitFor({ state: 'visible', timeout: 30000 });
      await loginBtn.click();
  
      // Screenshot después de login
      await page.screenshot({ path: 'screenshots/post_login.png', fullPage: true });
  
      console.log("Login ejecutado correctamente ✅");
  
    } catch (error) {
      // Captura de pantalla si falla el login
      await page.screenshot({ path: 'screenshots/fallo_login.png', fullPage: true });
      console.error("Fallo en login:", error);
      throw error;
    }
    
    await page.screenshot({ path: 'screenshots/antes_agenda.png', fullPage: true });

    // Click en botón Agenda con manejo de error y timeout extendido
    try {
      await page.getByRole('button', { name: 'Agenda' }).waitFor({ state: 'visible', timeout: 60000 });
      await page.getByRole('button', { name: 'Agenda' }).click();
    } catch (e) {
      await page.screenshot({ path: 'screenshots/fallo_agenda.png', fullPage: true });
      console.error("Fallo al hacer click en Agenda:", e);
      throw e;
    }

    // Click en NUEVOTURNO
    try {
      await page.locator('#NUEVOTURNO i').click({ timeout: 30000 });
    } catch (e) {
      await page.screenshot({ path: 'screenshots/fallo_nuevoturno.png', fullPage: true });
      console.error("Fallo al hacer click en NUEVOTURNO:", e);
      throw e;
    }

    // ====== BUSCAR ESPECIALIDAD ======
    const frame = await page.locator('#gxp0_ifrm').contentFrame();
    if (!frame) throw new Error("No se encontró el iframe de especialidades");

    try {
      await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).click();
      await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).fill("dermatologia");
      await frame.getByRole('textbox', { name: 'Buscar especialidad o' }).press("Enter");

      await frame.locator("div").filter({ hasText: /^DERMATOLOGIA$/ }).nth(3).click();
      await page.getByRole("button", { name: "Más tarde" }).click();
    } catch (e) {
      await page.screenshot({ path: 'screenshots/fallo_busqueda.png', fullPage: true });
      console.error("Fallo durante búsqueda de especialidad:", e);
      throw e;
    }

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
    // Captura general si falla cualquier otro paso
    await page.screenshot({ path: 'screenshots/error_general.png', fullPage: true });
    console.error("Error general:", error);
    throw error;
  } finally {
    await browser.close();
  }
}

main();
