# Rota Dash — Visão Geral do Projeto

## O que é

Bot Telegram que roda diariamente na Vercel: faz login no sistema Connect (Basic Telecom), baixa o relatório analítico XLSX do dia, processa os dados, gera uma imagem PNG do dashboard e envia para um grupo do Telegram.

## Stack

- **Next.js** (App Router) hospedado na Vercel — plano Hobby, maxDuration = 300s
- **Puppeteer** via `@sparticuz/chromium` (produção Vercel) / Chrome local (dev)
- **xlsx** para parsing do relatório
- **Satori** (JSX → SVG) + **Sharp** (SVG → PNG 2×) para geração da imagem
- **Telegram Bot API** — usa `sendDocument` (não `sendPhoto`) para preservar qualidade

## Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `app/api/cron/route.ts` | Endpoint cron — autenticado com `CRON_SECRET` |
| `lib/pipeline.ts` | Orquestra os 3 passos + envia status ao Telegram |
| `lib/connect.ts` | Login Puppeteer + download XLSX via CDP |
| `lib/processor.ts` | Parsing XLSX → `DashData` |
| `lib/image.tsx` | Satori JSX → Sharp PNG |
| `lib/telegram.ts` | `sendMessage` / `sendDocument` |
| `data/tipo.json` | Mapa `JOB COD → TIPO` (ex: "ADESAO INSTALACAO..." → "ADESÃO") |

## Variáveis de ambiente necessárias

| Variável | Descrição |
|---|---|
| `CONNECT_EMAIL` | Login no Connect |
| `CONNECT_PASSWORD` | Senha do Connect |
| `TELEGRAM_BOT_TOKEN` | Token do bot |
| `TELEGRAM_CHAT_ID` | ID do grupo |
| `CRON_SECRET` | Segredo para autenticar o endpoint `/api/cron` |

## Teste local

```bash
cp .env.local.example .env.local  # preencher as variáveis
npm run dev
curl -H "Authorization: Bearer <CRON_SECRET>" http://localhost:3000/api/cron
```
