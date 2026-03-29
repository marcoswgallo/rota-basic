// app/api/telegram/route.ts
import { after } from "next/server";
import {
  sendMessage,
  sendMessageWithKeyboard,
  answerCallbackQuery,
  sendDocumentFile,
  sendPhoto,
} from "@/lib/telegram";
import { runPipeline } from "@/lib/pipeline";
import { setConvState, getConvState, clearConvState } from "@/lib/state";
import { GRUPOS, processaPontuacao, geraExcelPontuacao } from "@/lib/pontuacao";
import { downloadRelatorio } from "@/lib/connect";

export const maxDuration = 300;

const CHAT_ID = process.env.TELEGRAM_CHAT_ID;
if (!CHAT_ID) throw new Error("TELEGRAM_CHAT_ID env var is not set");

const HELP = `🤖 Bot Rota Basic

Comandos:
/rodar      — rotina completa (Connect → imagem → Telegram)
/pontuacao  — ranking de técnicos por base (Excel)
/ping       — verifica se o bot está respondendo
/start      — mostra esta mensagem`;

// Teclado inline com as 9 bases disponíveis
const BASES_KEYBOARD = {
  inline_keyboard: [
    [
      { text: "BAURU", callback_data: "pon:BAURU" },
      { text: "RIBEIRAO PRETO", callback_data: "pon:RIBEIRAO PRETO" },
      { text: "CAMPINAS", callback_data: "pon:CAMPINAS" },
    ],
    [
      { text: "LIMEIRA", callback_data: "pon:LIMEIRA" },
      { text: "PAULINIA", callback_data: "pon:PAULINIA" },
      { text: "PIRACICABA", callback_data: "pon:PIRACICABA" },
    ],
    [
      { text: "SAO JOSE DO RIO PRETO", callback_data: "pon:SAO JOSE DO RIO PRETO" },
      { text: "SOROCABA", callback_data: "pon:SOROCABA" },
      { text: "SUMARE", callback_data: "pon:SUMARE" },
    ],
  ],
};

/** Converte "DD/MM/AAAA" para "AAAA-MM-DD". Retorna null se inválido. */
function parseDateBR(input: string): string | null {
  const m = input.trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return null;
  const [, d, mo, y] = m;
  const iso = `${y}-${mo}-${d}`;
  if (isNaN(new Date(`${iso}T00:00:00`).getTime())) return null;
  return iso;
}

/** Formata "AAAA-MM-DD" para "DD/MM/AAAA" */
function fmtDate(iso: string): string {
  const [y, mo, d] = iso.split("-");
  return `${d}/${mo}/${y}`;
}

/** Gera o nome do arquivo Excel: pontuacao_BAURU_01-03_28-03-2026.xlsx */
function xlsxFilename(base: string, dataIni: string, dataFim: string): string {
  const [, m1, d1] = dataIni.split("-");
  const [y2, m2, d2] = dataFim.split("-");
  const baseSlug = base.replace(/ /g, "_");
  return `pontuacao_${baseSlug}_${d1}-${m1}_${d2}-${m2}-${y2}.xlsx`;
}

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  // ─── Callback query (clique em botão inline) ───────────────────────────────
  const cbq = body.callback_query as Record<string, unknown> | undefined;
  if (cbq) {
    const cbChatId = String(
      ((cbq.message as Record<string, unknown>)?.chat as Record<string, unknown>)
        ?.id ?? ""
    );
    const cbData = String(cbq.data ?? "");
    const cbQueryId = String(cbq.id ?? "");

    // Sempre responde ao callback para remover o "loading" do botão
    await answerCallbackQuery(cbQueryId);

    if (cbChatId !== CHAT_ID) return new Response("ok");

    if (cbData.startsWith("pon:")) {
      const base = cbData.slice(4);
      setConvState(cbChatId, { step: "date_ini", base });
      await sendMessage(`Base: ${base}\n\nData inicial? (DD/MM/AAAA)`, cbChatId);
    }

    return new Response("ok");
  }

  // ─── Mensagens comuns ──────────────────────────────────────────────────────
  const msg =
    (body.message as Record<string, unknown>) ??
    (body.edited_message as Record<string, unknown>);

  if (!msg) return new Response("ok");

  const chatId = String(
    (msg.chat as Record<string, unknown>)?.id ?? ""
  );
  const text = String(msg.text ?? "").trim();

  if (chatId !== CHAT_ID) return new Response("ok");

  // ─── Estado de conversa (coleta de datas) ──────────────────────────────────
  if (!text.startsWith("/")) {
    const state = getConvState(chatId);

    if (state?.step === "date_ini") {
      const dataIni = parseDateBR(text);
      if (!dataIni) {
        await sendMessage("Formato inválido. Use DD/MM/AAAA:", chatId);
        return new Response("ok");
      }
      setConvState(chatId, { step: "date_fim", base: state.base, dataIni });
      await sendMessage("Data final? (DD/MM/AAAA)", chatId);
      return new Response("ok");
    }

    if (state?.step === "date_fim") {
      const dataFim = parseDateBR(text);
      if (!dataFim) {
        await sendMessage("Formato inválido. Use DD/MM/AAAA:", chatId);
        return new Response("ok");
      }
      if (dataFim < state.dataIni!) {
        await sendMessage(
          "A data final deve ser maior que a inicial. Informe novamente:",
          chatId
        );
        return new Response("ok");
      }

      const { base, dataIni } = state;
      clearConvState(chatId);

      await sendMessage(
        `⏳ Buscando dados de ${base} (${fmtDate(dataIni!)} → ${fmtDate(dataFim)})...`,
        chatId
      );

      after(async () => {
        try {
          const buffer = await downloadRelatorio(dataIni!, dataFim);
          const rows = processaPontuacao(buffer, base, dataIni!, dataFim);

          if (rows.length === 0) {
            await sendMessage(
              `⚠️ Nenhum dado encontrado para ${base} no período informado.`,
              chatId
            );
            return;
          }

          const excel = geraExcelPontuacao(rows);
          const filename = xlsxFilename(base, dataIni!, dataFim);
          await sendDocumentFile(
            excel,
            filename,
            `✅ Pontuação ${base} — ${rows.length} técnicos`,
            chatId
          );
        } catch (err: unknown) {
          const errMsg = err instanceof Error ? err.message : String(err);
          await sendMessage(`⛔ Erro ao buscar dados:\n${errMsg.slice(0, 800)}`, chatId);
        }
      });

      return new Response("ok");
    }

    return new Response("ok");
  }

  // ─── Comandos ──────────────────────────────────────────────────────────────
  const cmd = text.split(" ")[0].toLowerCase().split("@")[0];

  if (cmd === "/start" || cmd === "/help") {
    await sendMessage(HELP, chatId);
    return new Response("ok");
  }

  if (cmd === "/ping") {
    await sendMessage("🟢 Bot respondendo normalmente.", chatId);
    return new Response("ok");
  }

  if (cmd === "/rodar") {
    await sendMessage("⏳ Iniciando rotina...", chatId);
    after(async () => {
      await runPipeline(chatId);
    });
    return new Response("ok");
  }

  if (cmd === "/pontuacao") {
    await sendMessageWithKeyboard("Selecione a base:", BASES_KEYBOARD, chatId);
    return new Response("ok");
  }

  await sendMessage(
    "Comando não reconhecido. Use /start para ver os comandos.",
    chatId
  );
  return new Response("ok");
}
