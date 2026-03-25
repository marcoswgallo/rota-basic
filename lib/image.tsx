import satori from "satori";
import sharp from "sharp";
import type { DashData, BaseMetrics } from "./processor";

// ─── Helpers de formatação ────────────────────────────────────────────────────

const fmt = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (v: number) => `${fmt.format(v)}%`;
const fmtBRL = (v: number) => `R$ ${fmt.format(v)}`;
const fmtInt = (v: number) => String(Math.round(v));

// ─── Cores ────────────────────────────────────────────────────────────────────

const C = {
  header: "#1a1a1a",
  headerText: "#ffffff",
  rowEven: "#ffffff",
  rowOdd: "#f5f5f5",
  totalBg: "#1a1a1a",
  totalText: "#ffffff",
  border: "#cccccc",
  accent: "#e03030",
  title: "#ffffff",
  bg: "#111111",
};

// ─── Tipos de coluna ──────────────────────────────────────────────────────────

interface ColDef {
  label: string;
  width: number;
  value: (r: BaseMetrics) => string;
  align?: "left" | "right" | "center";
}

const COLS_MAIN: ColDef[] = [
  { label: "BASE",                     width: 220, value: r => r.base,                 align: "left"   },
  { label: "TÉCNICO",                  width: 72,  value: r => fmtInt(r.tecnicos),     align: "center" },
  { label: "CONTRATOS",                width: 90,  value: r => fmtInt(r.contratos),    align: "center" },
  { label: "%ND&ME",                   width: 82,  value: r => fmtPct(r.ndmePct),      align: "right"  },
  { label: "VALOR",                    width: 120, value: r => fmtBRL(r.valor),        align: "right"  },
  { label: "MÉDIA",                    width: 100, value: r => fmtBRL(r.media),        align: "right"  },
  { label: "MÉD. TÉC.",               width: 110, value: r => fmtBRL(r.medTec),       align: "right"  },
  { label: "POSSIB. FATURAMENTO",      width: 160, value: r => fmtBRL(r.possibilidade),align: "right"  },
];

const COLS_VT: ColDef[] = [
  { label: "BASE",      width: 180, value: r => r.base,             align: "left"   },
  { label: "TÉCNICO",   width: 72,  value: r => fmtInt(r.tecnicos), align: "center" },
  { label: "CONTRATOS", width: 90,  value: r => fmtInt(r.contratos),align: "center" },
  { label: "MÉDIA",     width: 100, value: r => fmtBRL(r.media),    align: "right"  },
];

const COLS_DESC: ColDef[] = [
  { label: "BASE",                     width: 220, value: r => r.base,                 align: "left"   },
  { label: "TÉCNICO",                  width: 72,  value: r => fmtInt(r.tecnicos),     align: "center" },
  { label: "CONTRATOS",                width: 90,  value: r => fmtInt(r.contratos),    align: "center" },
  { label: "VALOR",                    width: 120, value: r => fmtBRL(r.valor),        align: "right"  },
  { label: "MÉDIA",                    width: 100, value: r => fmtBRL(r.media),        align: "right"  },
  { label: "MÉD. TÉC.",               width: 110, value: r => fmtBRL(r.medTec),       align: "right"  },
  { label: "POSSIB. FATURAMENTO",      width: 160, value: r => fmtBRL(r.possibilidade),align: "right"  },
];

// ─── Componentes JSX para Satori ─────────────────────────────────────────────

function Table({
  cols,
  rows,
  total,
  fontSize = 11,
}: {
  cols: ColDef[];
  rows: BaseMetrics[];
  total: BaseMetrics;
  fontSize?: number;
}) {
  const rowH = 22;
  const headerH = 26;
  const tableW = cols.reduce((s, c) => s + c.width, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", border: `1px solid ${C.border}` }}>
      {/* Header */}
      <div style={{ display: "flex", height: headerH, background: C.header }}>
        {cols.map((col) => (
          <div
            key={col.label}
            style={{
              width: col.width,
              display: "flex",
              alignItems: "center",
              justifyContent: col.align === "right" ? "flex-end" : col.align === "center" ? "center" : "flex-start",
              padding: "0 6px",
              fontSize: fontSize - 1,
              fontWeight: 700,
              color: C.headerText,
              borderRight: `1px solid #333`,
            }}
          >
            {col.label}
          </div>
        ))}
      </div>

      {/* Linhas */}
      {rows.map((row, i) => (
        <div
          key={row.base}
          style={{
            display: "flex",
            height: rowH,
            background: i % 2 === 0 ? C.rowEven : C.rowOdd,
          }}
        >
          {cols.map((col) => (
            <div
              key={col.label}
              style={{
                width: col.width,
                display: "flex",
                alignItems: "center",
                justifyContent: col.align === "right" ? "flex-end" : col.align === "center" ? "center" : "flex-start",
                padding: "0 6px",
                fontSize,
                color: "#111",
                borderRight: `1px solid ${C.border}`,
                borderBottom: `1px solid ${C.border}`,
              }}
            >
              {col.value(row)}
            </div>
          ))}
        </div>
      ))}

      {/* Total */}
      <div style={{ display: "flex", height: rowH + 2, background: C.totalBg }}>
        {cols.map((col) => (
          <div
            key={col.label}
            style={{
              width: col.width,
              display: "flex",
              alignItems: "center",
              justifyContent: col.align === "right" ? "flex-end" : col.align === "center" ? "center" : "flex-start",
              padding: "0 6px",
              fontSize,
              fontWeight: 700,
              color: C.totalText,
              borderRight: "1px solid #333",
            }}
          >
            {col.value(total)}
          </div>
        ))}
      </div>
    </div>
  );
}

function Dashboard({ data }: { data: DashData }) {
  const mainW = COLS_MAIN.reduce((s, c) => s + c.width, 0);
  const vtW = COLS_VT.reduce((s, c) => s + c.width, 0);
  const descW = COLS_DESC.reduce((s, c) => s + c.width, 0);
  const totalW = mainW + 20 + vtW;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        background: C.bg,
        padding: 20,
        fontFamily: "Arial, sans-serif",
        width: totalW + 40,
      }}
    >
      {/* ── Cabeçalho ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: C.header,
          padding: "10px 20px",
          marginBottom: 14,
          borderRadius: 4,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ fontSize: 11, color: "#aaa", marginBottom: 2 }}>Basic Telecom</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: C.title, letterSpacing: 1 }}>
            Rota Inicial
          </div>
          <div style={{ fontSize: 10, color: "#888", marginTop: 2 }}>
            Referência: {data.dataRef}
          </div>
        </div>
      </div>

      {/* ── Bases normais + VT (lado a lado) ── */}
      <div style={{ display: "flex", gap: 20, marginBottom: 14 }}>
        <Table cols={COLS_MAIN} rows={data.bases} total={data.totalBases} />
        <Table cols={COLS_VT} rows={data.vt} total={data.totalVt} />
      </div>

      {/* ── Desconexão ── */}
      <Table cols={COLS_DESC} rows={data.desconexao} total={data.totalDesconexao} />
    </div>
  );
}

// ─── Função principal ─────────────────────────────────────────────────────────

export async function generateDashImage(data: DashData): Promise<Buffer> {
  // Satori não carrega fontes do sistema — usamos uma fonte base64 ou web font
  const fontRes = await fetch(
    "https://fonts.gstatic.com/s/arimo/v29/P5sfzZCDf9_T_3cV7NCUECyoxNk37cxsBxDAVQI4aA.woff"
  );
  const fontData = await fontRes.arrayBuffer();

  const svg = await satori(<Dashboard data={data} />, {
    width: 1400,
    height: 900,
    fonts: [
      {
        name: "Arial",
        data: fontData,
        weight: 400,
        style: "normal",
      },
    ],
  });

  // Converte SVG → PNG com sharp
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return png;
}
