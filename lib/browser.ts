import type { Browser } from "puppeteer-core";

/**
 * Retorna uma instância do browser:
 * - Em produção (Vercel): usa @sparticuz/chromium
 * - Em desenvolvimento: usa Chrome local
 */
export async function getBrowser(): Promise<Browser> {
  const puppeteer = await import("puppeteer-core");

  if (process.env.VERCEL || process.env.NODE_ENV === "production") {
    const chromium = await import("@sparticuz/chromium");
    chromium.default.setHeadlessMode = true;

    return puppeteer.default.launch({
      args: chromium.default.args,
      defaultViewport: chromium.default.defaultViewport,
      executablePath: await chromium.default.executablePath(),
      headless: true,
    });
  }

  // Desenvolvimento local — usa Chrome instalado
  const executablePath =
    process.platform === "darwin"
      ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
      : process.platform === "win32"
        ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        : "/usr/bin/google-chrome";

  return puppeteer.default.launch({
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    executablePath,
    headless: true,
  });
}
