import { downloadRelatorio, hoje } from "./connect";
import { processXlsx } from "./processor";
import { generateDashImage } from "./image";
import { sendMessage, sendPhoto } from "./telegram";

/**
 * Pipeline completo:
 * 1. Baixa XLSX do Connect
 * 2. Processa os dados
 * 3. Gera imagem PNG
 * 4. Envia no Telegram
 */
export async function runPipeline(chatId?: string) {
  const send = (text: string) => sendMessage(text, chatId);

  try {
    await send("🚀 [1/3] Baixando relatório do Connect...");
    const data = hoje();
    const buffer = await downloadRelatorio(data, data);

    await send("⚙️ [2/3] Processando dados...");
    const dashData = processXlsx(buffer);

    await send(`📸 [3/3] Gerando e enviando dashboard...`);
    const png = await generateDashImage(dashData);

    const caption =
      `📊 Rota Inicial — ${dashData.dataRef}\n` +
      `Bases: ${dashData.totalBases.contratos} contratos | R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2 }).format(dashData.totalBases.valor)}`;

    await sendPhoto(png, caption, chatId);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[pipeline] ERRO:", msg);
    await send(`⛔ Erro na rotina:\n${msg.slice(0, 800)}`);
    throw err;
  }
}
