const TOKEN = process.env.TELEGRAM_BOT_TOKEN!;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID!;
const API = `https://api.telegram.org/bot${TOKEN}`;

type InlineKeyboard = { text: string; callback_data: string }[][];

export async function sendMessage(text: string, chatId = CHAT_ID) {
  await fetch(`${API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}

export async function sendMessageWithKeyboard(
  text: string,
  keyboard: InlineKeyboard,
  chatId = CHAT_ID
) {
  await fetch(`${API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "Markdown",
      reply_markup: { inline_keyboard: keyboard },
    }),
  });
}

export async function answerCallbackQuery(callbackQueryId: string, text?: string) {
  await fetch(`${API}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text }),
  });
}

export async function sendPhoto(pngBuffer: Buffer, caption = "", chatId = CHAT_ID) {
  // sendDocument preserva qualidade original (sendPhoto comprime a imagem)
  const form = new FormData();
  form.append("chat_id", chatId);
  form.append("caption", caption);
  form.append("document", new Blob([new Uint8Array(pngBuffer)], { type: "image/png" }), "dash.png");

  const res = await fetch(`${API}/sendDocument`, { method: "POST", body: form });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Telegram sendDocument falhou: ${res.status} — ${body}`);
  }
}

export async function setWebhook(url: string) {
  const res = await fetch(`${API}/setWebhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, allowed_updates: ["message", "callback_query"] }),
  });
  return res.json();
}
