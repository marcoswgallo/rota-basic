# Pontuação de Técnicos por Base — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao bot Telegram o comando `/pontuacao` que conduz uma conversa passo a passo (base → data ini → data fim), baixa o relatório do Connect, soma `VALOR TÉCNICO` por técnico e envia um Excel com Técnico | Pontuação | Média | Projetado.

**Architecture:** Três partes independentes: (1) `lib/state.ts` gerencia estado em memória da conversa; (2) `lib/pontuacao.ts` contém os grupos de bases, cálculo de dias úteis e geração do XLSX; (3) `app/api/telegram/route.ts` recebe o novo comando `/pontuacao`, trata callback_query dos botões inline e percorre os passos de coleta de datas.

**Tech Stack:** Next.js 15 App Router, `xlsx` (já instalado), Telegram Bot API (inline keyboards + callback_query), TypeScript.

---

## Mapa de Arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `lib/state.ts` | Criar | Map em memória com TTL de 10 min para estado da conversa |
| `lib/pontuacao.ts` | Criar | Grupos de bases, diasUteis(), processaPontuacao(), geraExcelPontuacao() |
| `lib/telegram.ts` | Modificar | Adicionar sendMessageWithKeyboard(), answerCallbackQuery(), sendDocumentFile() |
| `app/api/telegram/route.ts` | Modificar | Adicionar /pontuacao, callback_query, parsing de datas |

---

## Task 1: lib/state.ts — Estado da Conversa

**Files:**
- Create: `lib/state.ts`

- [ ] **Step 1: Criar lib/state.ts**

```typescript
// lib/state.ts

interface ConvState {
  step: "date_ini" | "date_fim";
  base: string;
  dataIni?: string; // formato YYYY-MM-DD
  expires: number;  // timestamp ms
}

const states = new Map<string, ConvState>();

export function setConvState(
  chatId: string,
  state: Omit<ConvState, "expires">
): void {
  states.set(chatId, {
    ...state,
    expires: Date.now() + 10 * 60 * 1000,
  });
}

export function getConvState(chatId: string): ConvState | null {
  const s = states.get(chatId);
  if (!s) return null;
  if (Date.now() > s.expires) {
    states.delete(chatId);
    return null;
  }
  return s;
}

export function clearConvState(chatId: string): void {
  states.delete(chatId);
}
```

- [ ] **Step 2: Verificar compilação**

```bash
npx tsc --noEmit
```

Esperado: sem erros.

- [ ] **Step 3: Commit**

```bash
git add lib/state.ts
git commit -m "feat: add conversation state manager (lib/state.ts)"
```

---

## Task 2: lib/pontuacao.ts — Processamento e Excel

**Files:**
- Create: `lib/pontuacao.ts`

- [ ] **Step 1: Criar lib/pontuacao.ts**

```typescript
// lib/pontuacao.ts
import * as XLSX from "xlsx";

// ─── Grupos de bases ──────────────────────────────────────────────────────────
// Chave = nome exibido no bot | Valores = nomes exatos no XLSX (uppercase)
export const GRUPOS: Record<string, string[]> = {
  "BAURU":                 ["BASE BAURU", "GPON BAURU", "BASE BOTUCATU"],
  "RIBEIRAO PRETO":        ["BASE RIBEIRAO PRETO", "GPON RIBEIRAO PRETO"],
  "CAMPINAS":              ["BASE CAMPINAS"],
  "LIMEIRA":               ["BASE LIMEIRA"],
  "PAULINIA":              ["BASE PAULINIA"],
  "PIRACICABA":            ["BASE PIRACICABA"],
  "SAO JOSE DO RIO PRETO": ["BASE SAO JOSE DO RIO PRETO"],
  "SOROCABA":              ["BASE SOROCABA"],
  "SUMARE":                ["BASE SUMARE"],
};

export interface TecnicoRow {
  tecnico: string;
  pontuacao: number;
  media: number;
  projetado: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Conta dias de Segunda a Sábado (inclusive) no intervalo [ini, fim]. */
function diasUteis(ini: Date, fim: Date): number {
  let count = 0;
  const cur = new Date(ini);
  cur.setHours(0, 0, 0, 0);
  const end = new Date(fim);
  end.setHours(0, 0, 0, 0);
  while (cur <= end) {
    if (cur.getDay() !== 0) count++; // 0 = Domingo
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}

function parseValorTecnico(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const clean = v
      .replace(/R\$\s*/g, "")
      .replace(/\./g, "")
      .replace(",", ".")
      .trim();
    return parseFloat(clean) || 0;
  }
  return 0;
}

// ─── Processamento ────────────────────────────────────────────────────────────

/**
 * Lê o buffer XLSX, filtra pelas bases do grupo e retorna ranking de técnicos.
 * @param buffer   Buffer do XLSX baixado do Connect
 * @param grupo    Chave em GRUPOS (ex: "BAURU")
 * @param dataIni  Formato YYYY-MM-DD
 * @param dataFim  Formato YYYY-MM-DD
 */
export function processaPontuacao(
  buffer: Buffer,
  grupo: string,
  dataIni: string,
  dataFim: string
): TecnicoRow[] {
  const basesDoGrupo = new Set(
    (GRUPOS[grupo] ?? []).map((b) => b.toUpperCase())
  );

  const workbook = XLSX.read(buffer, { type: "buffer", cellDates: false });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet);

  const filtered = rows.filter((r) => {
    const base = String(r["BASE"] ?? "").trim().toUpperCase();
    return basesDoGrupo.has(base);
  });

  if (filtered.length === 0) return [];

  // Soma VALOR TÉCNICO por LOGIN
  const map = new Map<string, number>();
  for (const r of filtered) {
    const login = String(r["LOGIN"] ?? "").trim();
    if (!login) continue;
    const valor = parseValorTecnico(r["VALOR TÉCNICO"]);
    map.set(login, (map.get(login) ?? 0) + valor);
  }

  // Dias úteis decorridos (dataIni → dataFim)
  const ini = new Date(dataIni + "T00:00:00");
  const fim = new Date(dataFim + "T00:00:00");
  const decorridos = diasUteis(ini, fim);

  // Total de dias úteis do mês de dataFim
  const inicioMes = new Date(fim.getFullYear(), fim.getMonth(), 1);
  const fimMes = new Date(fim.getFullYear(), fim.getMonth() + 1, 0);
  const totalMes = diasUteis(inicioMes, fimMes);

  const result: TecnicoRow[] = [];
  for (const [tecnico, pontuacao] of map) {
    const media = decorridos > 0 ? pontuacao / decorridos : 0;
    const projetado = media * totalMes;
    result.push({ tecnico, pontuacao, media, projetado });
  }

  result.sort((a, b) => b.pontuacao - a.pontuacao);
  return result;
}

// ─── Geração do Excel ─────────────────────────────────────────────────────────

export function geraExcelPontuacao(rows: TecnicoRow[]): Buffer {
  const aoa = [
    ["Técnico", "Pontuação", "Média", "Projetado"],
    ...rows.map((r) => [
      r.tecnico,
      parseFloat(r.pontuacao.toFixed(2)),
      parseFloat(r.media.toFixed(2)),
      parseFloat(r.projetado.toFixed(2)),
    ]),
  ];
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Pontuação");
  return Buffer.from(XLSX.write(wb, { type: "buffer", bookType: "xlsx" }));
}
```

- [ ] **Step 2: Verificar compilação**

```bash
npx tsc --noEmit
```

Esperado: sem erros.

- [ ] **Step 3: Testar diasUteis manualmente via node**

```bash
node -e "
function diasUteis(ini, fim) {
  let count = 0;
  const cur = new Date(ini);
  cur.setHours(0,0,0,0);
  const end = new Date(fim);
  end.setHours(0,0,0,0);
  while (cur <= end) {
    if (cur.getDay() !== 0) count++;
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}
// Março 2026: 01/03(Dom) até 28/03(Sáb) = 28 dias - 4 domingos = 24
console.log('01/03 a 28/03:', diasUteis(new Date('2026-03-01'), new Date('2026-03-28')));
// Esperado: 24

// Total de março 2026: 31 dias - 5 domingos (1,8,15,22,29) = 26
console.log('total março:', diasUteis(new Date('2026-03-01'), new Date('2026-03-31')));
// Esperado: 26
"
```

Esperado:
```
01/03 a 28/03: 24
total março: 26
```

- [ ] **Step 4: Commit**

```bash
git add lib/pontuacao.ts
git commit -m "feat: add pontuacao processor and Excel generator (lib/pontuacao.ts)"
```

---

## Task 3: lib/telegram.ts — Novos helpers Telegram

**Files:**
- Modify: `lib/telegram.ts`

- [ ] **Step 1: Adicionar sendMessageWithKeyboard, answerCallbackQuery e sendDocumentFile**

Abrir [lib/telegram.ts](lib/telegram.ts) e adicionar ao final do arquivo (após a função `setWebhook`):

```typescript
export async function sendMessageWithKeyboard(
  text: string,
  inlineKeyboard: object,
  chatId = CHAT_ID
) {
  await fetch(`${API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      reply_markup: inlineKeyboard,
    }),
  });
}

export async function answerCallbackQuery(callbackQueryId: string) {
  await fetch(`${API}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId }),
  });
}

export async function sendDocumentFile(
  buffer: Buffer,
  filename: string,
  caption = "",
  chatId = CHAT_ID
) {
  const form = new FormData();
  form.append("chat_id", chatId);
  form.append("caption", caption);
  form.append(
    "document",
    new Blob([new Uint8Array(buffer)], { type: "application/octet-stream" }),
    filename
  );
  const res = await fetch(`${API}/sendDocument`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Telegram sendDocument falhou: ${res.status} — ${body}`);
  }
}
```

- [ ] **Step 2: Atualizar setWebhook para incluir callback_query**

Localizar a linha com `allowed_updates: ["message"]` e alterar para:

```typescript
body: JSON.stringify({ url, allowed_updates: ["message", "callback_query"] }),
```

- [ ] **Step 3: Verificar compilação**

```bash
npx tsc --noEmit
```

Esperado: sem erros.

- [ ] **Step 4: Commit**

```bash
git add lib/telegram.ts
git commit -m "feat: add sendMessageWithKeyboard, answerCallbackQuery, sendDocumentFile to telegram lib"
```

---

## Task 4: app/api/telegram/route.ts — Comando /pontuacao

**Files:**
- Modify: `app/api/telegram/route.ts`

- [ ] **Step 1: Substituir o conteúdo do arquivo pelo novo**

```typescript
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

const CHAT_ID = process.env.TELEGRAM_CHAT_ID!;

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
```

- [ ] **Step 2: Verificar compilação**

```bash
npx tsc --noEmit
```

Esperado: sem erros.

- [ ] **Step 3: Commit**

```bash
git add app/api/telegram/route.ts
git commit -m "feat: add /pontuacao command with inline keyboard and date conversation flow"
```

---

## Task 5: Deploy e re-registro do webhook

**Files:** nenhum arquivo novo.

- [ ] **Step 1: Build de verificação**

```bash
npm run build
```

Esperado: build completo sem erros de TypeScript ou bundling.

- [ ] **Step 2: Deploy na Vercel**

```bash
git push origin main
```

Aguardar o deploy completar no dashboard da Vercel.

- [ ] **Step 3: Re-registrar o webhook do Telegram**

O webhook precisa ser re-registrado para incluir `callback_query` no `allowed_updates`. Chamar a rota de setup existente ou fazer diretamente via curl (substituir `<TOKEN>` e `<URL>`):

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"<URL>/api/telegram","allowed_updates":["message","callback_query"]}'
```

Esperado: `{"ok":true,"result":true,"description":"Webhook was set"}`

- [ ] **Step 4: Smoke test no Telegram**

1. Enviar `/pontuacao` no grupo
2. Confirmar que o teclado inline aparece com as 9 bases
3. Clicar em "BAURU"
4. Confirmar mensagem "Base: BAURU\n\nData inicial? (DD/MM/AAAA)"
5. Enviar `01/03/2026`
6. Confirmar mensagem "Data final? (DD/MM/AAAA)"
7. Enviar `28/03/2026`
8. Confirmar mensagem "⏳ Buscando dados de BAURU (01/03/2026 → 28/03/2026)..."
9. Aguardar e confirmar recebimento do arquivo `.xlsx` com as colunas Técnico | Pontuação | Média | Projetado

- [ ] **Step 5: Testar erro de data inválida**

1. Enviar `/pontuacao`, clicar em qualquer base
2. Enviar `abc` — confirmar "Formato inválido. Use DD/MM/AAAA:"
3. Enviar uma data válida para continuar o fluxo normalmente

- [ ] **Step 6: Testar data final menor que inicial**

1. Enviar `/pontuacao`, clicar em qualquer base
2. Enviar `28/03/2026` como data inicial
3. Enviar `01/03/2026` como data final
4. Confirmar "A data final deve ser maior que a inicial. Informe novamente:"
