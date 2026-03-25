import { getBrowser } from "./browser";

const BASE_URL = "https://basic.controlservices.com.br";
const LOGIN_URL = `${BASE_URL}/login`;
const REL_URL = `${BASE_URL}/financeiro/relatorio`;

const PAGE_LOAD_TIMEOUT = parseInt(process.env.PAGE_LOAD_TIMEOUT ?? "90000");
const DOWNLOAD_TIMEOUT = parseInt(process.env.DOWNLOAD_TIMEOUT ?? "300000");

/**
 * Faz login no Connect, seleciona o Relatório Analítico do dia
 * e retorna o conteúdo do XLSX como Buffer.
 */
export async function downloadRelatorio(dataIni: string, dataFim: string): Promise<Buffer> {
  const email = process.env.CONNECT_EMAIL;
  const password = process.env.CONNECT_PASSWORD;

  if (!email || !password) {
    throw new Error("Defina CONNECT_EMAIL e CONNECT_PASSWORD nas env vars.");
  }

  const browser = await getBrowser();

  try {
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(PAGE_LOAD_TIMEOUT);
    page.setDefaultTimeout(PAGE_LOAD_TIMEOUT);

    // ─── Login ───────────────────────────────────────────
    console.log("[connect] Abrindo login...");
    await page.goto(LOGIN_URL, { waitUntil: "domcontentloaded" });

    await page.waitForSelector('[name="email"]');
    await page.type('[name="email"]', email);
    await page.type('[name="password"]', password);
    await page.click('button[type="submit"]');

    await page.waitForNavigation({ waitUntil: "domcontentloaded" });
    if (!page.url().includes("/home")) {
      throw new Error("Login falhou — verifique CONNECT_EMAIL e CONNECT_PASSWORD.");
    }
    console.log("[connect] Login OK.");

    // ─── Página do relatório ─────────────────────────────
    console.log("[connect] Abrindo página do relatório...");
    await page.goto(REL_URL, { waitUntil: "domcontentloaded" });

    // Seleciona "Relatorio Analitico"
    await page.waitForSelector('[name="tipoRelat"]');
    await page.select('[name="tipoRelat"]', await page.evaluate(() => {
      const sel = document.querySelector('[name="tipoRelat"]') as HTMLSelectElement;
      const opt = Array.from(sel.options).find(o =>
        o.text.includes("Analitico") || o.text.includes("Analítico")
      );
      return opt?.value ?? "";
    }));

    // Preenche datas via JS (evita problema com inputs tipo date)
    await page.evaluate((ini, fim) => {
      const setVal = (name: string, val: string) => {
        const el = document.querySelector(`[name="${name}"]`) as HTMLInputElement;
        if (el) { el.value = val; el.dispatchEvent(new Event("input", { bubbles: true })); }
      };
      setVal("data_ini", ini);
      setVal("data_fim", fim);
    }, dataIni, dataFim);

    // Marca checkbox EXCEL
    await page.evaluate(() => {
      const labels = Array.from(document.querySelectorAll("label"));
      const excelLabel = labels.find(l => l.textContent?.toUpperCase().includes("EXCEL"));
      if (excelLabel) {
        const forAttr = excelLabel.getAttribute("for");
        if (forAttr) {
          const cb = document.getElementById(forAttr) as HTMLInputElement;
          if (cb && !cb.checked) cb.click();
          return;
        }
      }
      // fallback
      const checkboxes = Array.from(document.querySelectorAll<HTMLInputElement>("input[type='checkbox']"));
      const excelCb = checkboxes.find(cb => {
        const sib = cb.closest("label")?.textContent ?? cb.nextElementSibling?.textContent ?? "";
        return sib.toUpperCase().includes("EXCEL");
      });
      if (excelCb && !excelCb.checked) excelCb.click();
    });

    // ─── Intercepta download via CDP ────────────────────
    // Em vez de salvar em disco, capturamos o conteúdo em memória
    const cdpSession = await page.createCDPSession();
    await cdpSession.send("Page.setDownloadBehavior", {
      behavior: "deny", // bloqueia download real — vamos interceptar
    });

    // Intercepta a response do XLSX via request interception
    let xlsxBuffer: Buffer | null = null;
    const downloadPromise = new Promise<Buffer>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Timeout aguardando XLSX")), DOWNLOAD_TIMEOUT);

      page.on("response", async (response) => {
        const url = response.url();
        const ct = response.headers()["content-type"] ?? "";
        const cd = response.headers()["content-disposition"] ?? "";

        const isXlsx =
          ct.includes("spreadsheet") ||
          ct.includes("excel") ||
          ct.includes("octet-stream") ||
          cd.includes(".xlsx") ||
          cd.includes("filename");

        if (isXlsx) {
          try {
            const buf = await response.buffer();
            clearTimeout(timer);
            resolve(buf);
          } catch (e) {
            clearTimeout(timer);
            reject(e);
          }
        }
      });

      // Rejeita se a página navegar para erro
      page.on("requestfailed", (req) => {
        if (req.url().includes("relatorio") || req.url().includes("export")) {
          clearTimeout(timer);
          reject(new Error(`Request falhou: ${req.url()}`));
        }
      });
    });

    // Clica em BUSCAR
    console.log("[connect] Clicando em BUSCAR...");
    const clicked = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll<HTMLButtonElement>("button"));
      const btn = btns.find(b => b.textContent?.toUpperCase().includes("BUSCAR"));
      if (btn) { btn.click(); return true; }
      return false;
    });
    if (!clicked) throw new Error("Botão BUSCAR não encontrado.");

    console.log("[connect] Aguardando download do XLSX...");
    xlsxBuffer = await downloadPromise;
    console.log(`[connect] XLSX recebido (${(xlsxBuffer.length / 1024).toFixed(1)} KB).`);

    return xlsxBuffer;
  } finally {
    await browser.close();
  }
}

/** Retorna data no formato YYYY-MM-DD para hoje */
export function hoje(): string {
  return new Date().toISOString().split("T")[0];
}
