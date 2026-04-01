import { after } from "next/server";
import { sendMessage, sendMessageWithKeyboard, answerCallbackQuery } from "@/lib/telegram";
import { runPipeline } from "@/lib/pipeline";

// Permite até 800s para o Fluid Compute completar o pipeline
export const maxDuration = 300;

const CHAT_ID = process.env.TELEGRAM_CHAT_ID!;

const MENU_TEXT = `🤖 *Bot Rota Basic*

Escolha uma opção:`;

const MENU_KEYBOARD = [
  [{ text: "📊 Rota Completa", callback_data: "rodar_completo" }],
  [{ text: "⏱ Rota Parcial (até agora)", callback_data: "rodar_parcial" }],
];

function dataKeyboard(tipo: "completo" | "parcial") {
  return [
    [{ text: "📅 Hoje", callback_data: `data_${tipo}_hoje` }],
    [{ text: "📅 Ontem", callback_data: `data_${tipo}_ontem` }],
  ];
}

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

  // Trata clique em botão inline
  const callbackQuery = body.callback_query as Record<string, unknown> | undefined;
  if (callbackQuery) {
    const callbackQueryId = String(callbackQuery.id ?? "");
    const callbackChatId = String(
      ((callbackQuery.message as Record<string, unknown>)?.chat as Record<string, unknown>)?.id ?? ""
    );
    const callbackData = String(callbackQuery.data ?? "");

    if (callbackChatId !== CHAT_ID) return new Response("ok");

    // Confirma o clique para o Telegram (remove o "loading" no botão)
    await answerCallbackQuery(callbackQueryId);

    if (callbackData === "rodar_completo") {
      await sendMessage("⏳ Iniciando rota completa (hoje)...", callbackChatId);
      after(async () => { await runPipeline(callbackChatId, "completo", "hoje"); });
    } else if (callbackData === "rodar_parcial") {
      await sendMessageWithKeyboard("📅 Qual data?", dataKeyboard("parcial"), callbackChatId);
    } else if (callbackData === "data_completo_hoje") {
      await sendMessage("⏳ Iniciando rota completa (hoje)...", callbackChatId);
      after(async () => { await runPipeline(callbackChatId, "completo", "hoje"); });
    } else if (callbackData === "data_completo_ontem") {
      await sendMessage("⏳ Iniciando rota completa (ontem)...", callbackChatId);
      after(async () => { await runPipeline(callbackChatId, "completo", "ontem"); });
    } else if (callbackData === "data_parcial_hoje") {
      await sendMessage("⏳ Iniciando rota parcial (hoje)...", callbackChatId);
      after(async () => { await runPipeline(callbackChatId, "parcial", "hoje"); });
    } else if (callbackData === "data_parcial_ontem") {
      await sendMessage("⏳ Iniciando rota parcial (ontem)...", callbackChatId);
      after(async () => { await runPipeline(callbackChatId, "parcial", "ontem"); });
    }

    return new Response("ok");
  }

  // Trata mensagens de texto / comandos
  const msg =
    (body.message as Record<string, unknown>) ??
    (body.edited_message as Record<string, unknown>);

  if (!msg) return new Response("ok");

  const chatId = String((msg.chat as Record<string, unknown>)?.id ?? "");
  const text = String(msg.text ?? "").trim();

  // Segurança: só responde ao chat configurado
  if (chatId !== CHAT_ID) return new Response("ok");

  if (!text.startsWith("/")) return new Response("ok");

  const cmd = text.split(" ")[0].toLowerCase().split("@")[0];

  if (cmd === "/start" || cmd === "/help") {
    await sendMessageWithKeyboard(MENU_TEXT, MENU_KEYBOARD, chatId);
    return new Response("ok");
  }

  if (cmd === "/ping") {
    await sendMessage("🟢 Bot respondendo normalmente.", chatId);
    return new Response("ok");
  }

  if (cmd === "/rodar") {
    await sendMessage("⏳ Iniciando rota completa (hoje)...", chatId);
    after(async () => { await runPipeline(chatId, "completo", "hoje"); });
    return new Response("ok");
  }

  if (cmd === "/parcial") {
    await sendMessageWithKeyboard("📅 Qual data?", dataKeyboard("parcial"), chatId);
    return new Response("ok");
  }

  await sendMessage("Comando não reconhecido. Use /start para ver os comandos.", chatId);
  return new Response("ok");
}
