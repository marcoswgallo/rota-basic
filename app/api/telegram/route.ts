import { after } from "next/server";
import { sendMessage } from "@/lib/telegram";
import { runPipeline } from "@/lib/pipeline";

// Permite até 800s para o Fluid Compute completar o pipeline
export const maxDuration = 800;

const CHAT_ID = process.env.TELEGRAM_CHAT_ID!;

const HELP = `🤖 *Bot Rota Basic*

Comandos:
/rodar — rotina completa (Connect → imagem → Telegram)
/ping  — verifica se o bot está respondendo
/start — mostra esta mensagem`;

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return new Response("bad request", { status: 400 });
  }

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
    await sendMessage(HELP, chatId);
    return new Response("ok");
  }

  if (cmd === "/ping") {
    await sendMessage("🟢 Bot respondendo normalmente.", chatId);
    return new Response("ok");
  }

  if (cmd === "/rodar") {
    // Responde imediatamente e processa em background
    await sendMessage("⏳ Iniciando rotina...", chatId);

    after(async () => {
      await runPipeline(chatId);
    });

    return new Response("ok");
  }

  await sendMessage("Comando não reconhecido. Use /start para ver os comandos.", chatId);
  return new Response("ok");
}
