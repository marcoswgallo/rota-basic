import { downloadRelatorio, hoje, ontem } from "./connect";
import { processXlsx } from "./processor";
import { generateDashImage } from "./image";
import { sendMessage, sendPhoto } from "./telegram";

export type TipoDash = "completo" | "parcial";
export type DataDash = "hoje" | "ontem";

/**
 * Pipeline completo:
 * 1. Baixa XLSX do Connect
 * 2. Processa os dados (parcial filtra por STATUS produtivo)
 * 3. Gera imagem PNG
 * 4. Envia no Telegram
 */
export async function runPipeline(chatId?: string, tipo: TipoDash = "completo", dataDash: DataDash = "hoje") {
  const send = (text: string) => sendMessage(text, chatId);
  const isParcial = tipo === "parcial";

  try {
    await send("🚀 [1/3] Baixando relatório do Connect...");
    const data = dataDash === "ontem" ? ontem() : hoje();
    const buffer = await downloadRelatorio(data, data);

    await send("⚙️ [2/3] Processando dados...");
    const dashData = processXlsx(buffer, isParcial);

    await send(`📸 [3/3] Gerando e enviando dashboard...`);
    const png = await generateDashImage(dashData, tipo);

    const diaLabel = dataDash === "ontem" ? "Ontem" : "Hoje";
    const label = isParcial ? `Rota Parcial (${diaLabel})` : `Rota Inicial (${diaLabel})`;
    const caption =
      `📊 ${label} — ${dashData.dataRef}\n` +
      `Bases: ${dashData.totalBases.contratos} contratos | R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2 }).format(dashData.totalBases.valor)}`;

    await sendPhoto(png, caption, chatId);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[pipeline] ERRO:", msg);
    await send(`⛔ Erro na rotina:\n${msg.slice(0, 800)}`);
    throw err;
  }
}
