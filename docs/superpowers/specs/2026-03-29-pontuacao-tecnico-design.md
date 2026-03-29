# Spec: Comando /pontuacao — Ranking de Técnicos por Base

**Data:** 2026-03-29
**Status:** Aprovado

---

## Visão Geral

Adicionar ao bot Telegram o comando `/pontuacao` que permite ao usuário consultar o ranking de pontuação dos técnicos de uma base específica para um período informado. O bot conduz uma conversa passo a passo (base → data inicial → data final), baixa o relatório do Connect, processa a coluna `VALOR TÉCNICO` e envia um arquivo Excel com os resultados.

---

## Arquivos Envolvidos

| Arquivo | Ação |
|---|---|
| `lib/state.ts` | Novo — gerencia estado da conversa em memória |
| `lib/pontuacao.ts` | Novo — processa VALOR TÉCNICO e gera XLSX |
| `app/api/telegram/route.ts` | Modificado — adiciona `/pontuacao` e `callback_query` |

---

## Fluxo da Conversa

```
Usuário: /pontuacao
Bot: "Selecione a base:" [teclado inline com 9 botões]

Usuário: clica em "BAURU"
Bot: salva estado {step:"date_ini", base:"BAURU"}
Bot: "Data inicial? (DD/MM/AAAA)"

Usuário: "01/03/2026"
Bot: salva estado {step:"date_fim", base:"BAURU", dataIni:"2026-03-01"}
Bot: "Data final? (DD/MM/AAAA)"

Usuário: "28/03/2026"
Bot: apaga estado
Bot: "⏳ Buscando dados de BAURU (01/03 → 28/03/2026)..."
Bot: [processa em background via after()]
Bot: envia "pontuacao_BAURU_01-03_28-03-2026.xlsx"
Bot: "✅ Pontuação BAURU — 28 técnicos"
```

---

## Estado em Memória (`lib/state.ts`)

```typescript
interface ConvState {
  step: "date_ini" | "date_fim";
  base: string;
  dataIni?: string;   // formato YYYY-MM-DD
  expires: number;    // Date.now() + 10 * 60 * 1000
}

Map<chatId: string, ConvState>
```

- TTL: 10 minutos
- Limpeza: verificada a cada leitura (lazy expiry)
- Sem dependências externas — estado local ao processo Node.js

---

## Grupos de Bases (`lib/pontuacao.ts`)

```typescript
const GRUPOS: Record<string, string[]> = {
  "BAURU":                  ["BASE BAURU", "GPON BAURU", "BASE BOTUCATU"],
  "RIBEIRAO PRETO":         ["BASE RIBEIRAO PRETO", "GPON RIBEIRAO PRETO"],
  "CAMPINAS":               ["BASE CAMPINAS"],
  "LIMEIRA":                ["BASE LIMEIRA"],
  "PAULINIA":               ["BASE PAULINIA"],
  "PIRACICABA":             ["BASE PIRACICABA"],
  "SAO JOSE DO RIO PRETO":  ["BASE SAO JOSE DO RIO PRETO"],
  "SOROCABA":               ["BASE SOROCABA"],
  "SUMARE":                 ["BASE SUMARE"],
};
```

Filtragem: `BASE` do XLSX convertido para uppercase comparado contra os valores do grupo.

---

## Processamento (`lib/pontuacao.ts`)

### Leitura do VALOR TÉCNICO

- Coluna usada: `VALOR TÉCNICO`
- Agrupamento: por `LOGIN` (nome completo do técnico)
- Agregação: soma simples de todos os valores do período para aquele LOGIN
- Sem lógica de distinct por contrato (diferente do pipeline principal)

### Cálculo de Dias Úteis (Segunda a Sábado, sem Domingo)

```typescript
function diasUteis(ini: Date, fim: Date): number {
  // conta dias de segunda (1) a sábado (6) entre ini e fim inclusive
}

// Dias decorridos: de dataIni até dataFim
const decorridos = diasUteis(dataIni, dataFim);

// Total do mês: do dia 1 até o último dia do mês de dataFim
const inicioMes = new Date(dataFim.getFullYear(), dataFim.getMonth(), 1);
const fimMes = new Date(dataFim.getFullYear(), dataFim.getMonth() + 1, 0);
const totalMes = diasUteis(inicioMes, fimMes);
```

### Fórmulas das Colunas

| Coluna | Fórmula |
|---|---|
| Técnico | Valor do campo `LOGIN` |
| Pontuação | `Σ VALOR TÉCNICO` do técnico no período |
| Média | `Pontuação ÷ dias úteis decorridos` |
| Projetado | `Média × total dias úteis do mês` |

- Ordenação: Pontuação decrescente
- Valores numéricos: 2 casas decimais no Excel

---

## Excel Gerado

- Biblioteca: `xlsx` (já instalada)
- Uma aba: `Pontuação`
- Colunas: `Técnico | Pontuação | Média | Projetado`
- Nome do arquivo: `pontuacao_BAURU_01-03_28-03-2026.xlsx`
- Enviado via `sendDocument` (mesmo método do dashboard)

---

## Tratamento de Erros

| Situação | Resposta do bot |
|---|---|
| Data digitada em formato inválido | "Formato inválido. Use DD/MM/AAAA:" (mantém estado) |
| dataFim < dataIni | "A data final deve ser maior que a inicial. Informe novamente:" |
| XLSX sem dados para a base/período | "⚠️ Nenhum dado encontrado para BAURU no período informado." |
| Erro no Connect / download | "⛔ Erro ao buscar dados:\n[mensagem]" |

---

## Alterações em `app/api/telegram/route.ts`

1. Importar `setConvState`, `getConvState`, `clearConvState` de `lib/state.ts`
2. Importar `processaPontuacao`, `GRUPOS` de `lib/pontuacao.ts`
3. Adicionar handling de `callback_query` (para o clique nos botões inline)
4. Adicionar parsing do passo `date_ini` e `date_fim` no handler de mensagens de texto
5. Adicionar comando `/pontuacao` que envia o teclado inline
6. Atualizar o texto do `/help` com o novo comando
7. Permitir `allowed_updates: ["message", "callback_query"]` no `setWebhook`

---

## Fora do Escopo

- Consolidado de múltiplas bases em uma única consulta (pode ser feito numa segunda iteração)
- Persistência de estado entre cold starts (in-memory é suficiente para o volume atual)
- Autenticação por usuário (bot já restringe ao `CHAT_ID` configurado)
