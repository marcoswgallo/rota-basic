import * as XLSX from "xlsx";
import tipoRaw from "@/data/tipo.json";

// Mapa OS → TIPO (ex: "ADESAO INSTALACAO..." → "ADESÃO")
const TIPO_MAP: Record<string, string> = {};
for (const row of tipoRaw as { OS: string; TIPO: string }[]) {
  TIPO_MAP[row.OS.trim().toUpperCase()] = row.TIPO.trim();
}

// TIPOs que contam como ND&ME
const NDME_TIPOS = new Set(["ADESÃO", "MUD ENDEREÇO"]);

export interface BaseMetrics {
  base: string;
  tecnicos: number;
  contratos: number;
  ndmePct: number;   // ex: 56.48 (já em %)
  valor: number;
  media: number;
  medTec: number;
  possibilidade: number;
}

export interface DashData {
  bases: BaseMetrics[];      // bases normais
  vt: BaseMetrics[];         // bases VT
  desconexao: BaseMetrics[]; // DESCONEXÃO
  dataRef: string;           // data de referência do relatório
  totalBases: BaseMetrics;   // totalizador das bases normais
  totalVt: BaseMetrics;      // totalizador das bases VT
  totalDesconexao: BaseMetrics;
}

function parseValor(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    // Remove "R$", espaços e troca vírgula decimal por ponto
    const clean = v.replace(/R\$\s*/g, "").replace(/\./g, "").replace(",", ".").trim();
    return parseFloat(clean) || 0;
  }
  return 0;
}

function calcMetrics(base: string, rows: Record<string, unknown>[]): BaseMetrics {
  const tecnicos = new Set(rows.map((r) => String(r["LOGIN"] ?? "").trim())).size;
  const contratos = rows.length;

  let ndmeCount = 0;
  let valor = 0;

  for (const r of rows) {
    const tipoOs = String(r["TIPO OS"] ?? "").trim().toUpperCase();
    const tipo = TIPO_MAP[tipoOs] ?? "";
    if (NDME_TIPOS.has(tipo)) ndmeCount++;
    valor += parseValor(r["VALOR EMPRESA"]);
  }

  const ndmePct = contratos > 0 ? (ndmeCount / contratos) * 100 : 0;
  const media = contratos > 0 ? valor / contratos : 0;
  const medTec = tecnicos > 0 ? valor / tecnicos : 0;
  const possibilidade = valor * 0.75;

  return { base, tecnicos, contratos, ndmePct, valor, media, medTec, possibilidade };
}

function totalize(label: string, list: BaseMetrics[]): BaseMetrics {
  const tecnicos = list.reduce((s, b) => s + b.tecnicos, 0);
  const contratos = list.reduce((s, b) => s + b.contratos, 0);
  const valor = list.reduce((s, b) => s + b.valor, 0);

  // %ND&ME do total: proporcional ao número de contratos
  const ndmeWeighted = list.reduce((s, b) => s + (b.ndmePct / 100) * b.contratos, 0);
  const ndmePct = contratos > 0 ? (ndmeWeighted / contratos) * 100 : 0;

  const media = contratos > 0 ? valor / contratos : 0;
  const medTec = tecnicos > 0 ? valor / tecnicos : 0;
  const possibilidade = valor * 0.75;

  return { base: label, tecnicos, contratos, ndmePct, valor, media, medTec, possibilidade };
}

export function processXlsx(buffer: Buffer): DashData {
  const workbook = XLSX.read(buffer, { type: "buffer", cellDates: false });
  const sheetName = workbook.SheetNames[0];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(
    workbook.Sheets[sheetName]
  );

  if (rows.length === 0) throw new Error("Relatório vazio — nenhuma linha encontrada.");

  // Data de referência: campo DATA_TOA da primeira linha
  const dataRef = String(rows[0]["DATA_TOA"] ?? rows[0]["DATA"] ?? "").split(" ")[0];

  // Agrupa por BASE
  const byBase = new Map<string, Record<string, unknown>[]>();
  for (const row of rows) {
    const base = String(row["BASE"] ?? "").trim().toUpperCase();
    if (!base) continue;
    if (!byBase.has(base)) byBase.set(base, []);
    byBase.get(base)!.push(row);
  }

  const bases: BaseMetrics[] = [];
  const vt: BaseMetrics[] = [];
  const desconexao: BaseMetrics[] = [];

  for (const [base, rowsForBase] of byBase) {
    const metrics = calcMetrics(base, rowsForBase);
    if (base.includes("DESCONEX")) {
      desconexao.push(metrics);
    } else if (/ VT$/.test(base) || base.endsWith(" VT")) {
      vt.push(metrics);
    } else {
      bases.push(metrics);
    }
  }

  bases.sort((a, b) => a.base.localeCompare(b.base, "pt-BR"));
  vt.sort((a, b) => a.base.localeCompare(b.base, "pt-BR"));
  desconexao.sort((a, b) => a.base.localeCompare(b.base, "pt-BR"));

  return {
    bases,
    vt,
    desconexao,
    dataRef,
    totalBases: totalize("Total", bases),
    totalVt: totalize("Total", vt),
    totalDesconexao: totalize("Total", desconexao),
  };
}
