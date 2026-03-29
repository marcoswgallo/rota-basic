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
