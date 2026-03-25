const TOKEN = process.env.TELEGRAM_BOT_TOKEN!;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID!;
const API = `https://api.telegram.org/bot${TOKEN}`;

export async function sendMessage(text: string, chatId = CHAT_ID) {
  await fetch(`${API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}

export async function sendPhoto(pngBuffer: Buffer, caption = "", chatId = CHAT_ID) {
  const form = new FormData();
  form.append("chat_id", chatId);
  form.append("caption", caption);
  form.append("photo", new Blob([new Uint8Array(pngBuffer)], { type: "image/png" }), "dash.png");

  const res = await fetch(`${API}/sendPhoto`, { method: "POST", body: form });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Telegram sendPhoto falhou: ${res.status} — ${body}`);
  }
}

export async function setWebhook(url: string) {
  const res = await fetch(`${API}/setWebhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, allowed_updates: ["message"] }),
  });
  return res.json();
}
