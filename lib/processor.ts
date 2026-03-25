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

  // Agrupa por contrato para garantir distinct em contratos, ND&ME e valor
  const contratoMap = new Map<string, { isNdme: boolean; valor: number }>();
  for (const r of rows) {
    const contrato = String(r["CONTRATO"] ?? "").trim();
    if (!contrato) continue;
    const tipoOs = String(r["JOB COD"] ?? "").trim().toUpperCase();
    const isNdme = NDME_TIPOS.has(TIPO_MAP[tipoOs] ?? "");
    if (!contratoMap.has(contrato)) {
      contratoMap.set(contrato, { isNdme, valor: parseValor(r["VALOR EMPRESA"]) });
    } else if (isNdme) {
      contratoMap.get(contrato)!.isNdme = true;
    }
  }

  const contratos = contratoMap.size;
  let ndmeCount = 0;
  let valor = 0;
  for (const entry of contratoMap.values()) {
    if (entry.isNdme) ndmeCount++;
    valor += entry.valor;
  }

  const ndmePct = contratos > 0 ? (ndmeCount / contratos) * 100 : 0;
  const media = tecnicos > 0 ? contratos / tecnicos : 0;   // contratos por técnico
  const medTec = tecnicos > 0 ? valor / tecnicos : 0;      // valor por técnico
  const possibilidade = valor * 0.75;

  return { base, tecnicos, contratos, ndmePct, valor, media, medTec, possibilidade };
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

  // Rows brutas por grupo — para calcular totais com distinct correto
  const rowsBases: Record<string, unknown>[] = [];
  const rowsVt: Record<string, unknown>[] = [];
  const rowsDesconexao: Record<string, unknown>[] = [];

  for (const [base, rowsForBase] of byBase) {
    const metrics = calcMetrics(base, rowsForBase);
    if (base.includes("DESCONEX")) {
      desconexao.push(metrics);
      rowsDesconexao.push(...rowsForBase);
    } else if (/ VT$/.test(base) || base.endsWith(" VT")) {
      vt.push(metrics);
      rowsVt.push(...rowsForBase);
    } else if (base.includes("MDU") || base.includes("VAR")) {
      // Bases MDU e VAR não aparecem no dashboard
    } else {
      bases.push(metrics);
      rowsBases.push(...rowsForBase);
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
    // Totais calculados com distinct sobre as rows brutas do grupo
    totalBases: calcMetrics("Total", rowsBases),
    totalVt: calcMetrics("Total", rowsVt),
    totalDesconexao: calcMetrics("Total", rowsDesconexao),
  };
}
