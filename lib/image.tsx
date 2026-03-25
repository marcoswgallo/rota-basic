import React from "react";
import satori from "satori";
import sharp from "sharp";
import type { DashData, BaseMetrics } from "./processor";

// ─── Helpers de formatação ────────────────────────────────────────────────────

const fmt    = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (v: number) => `${fmt.format(v)}%`;
const fmtBRL = (v: number) => `R$ ${fmt.format(v)}`;
const fmtInt = (v: number) => String(Math.round(v));

// ─── Paleta Opção B — Clean Light ─────────────────────────────────────────────

const C = {
  bg:          "#f4f6f9",
  headerBg:    "#1a202c",
  headerText:  "#ffffff",
  rowEven:     "#ffffff",
  rowOdd:      "#f8fafc",
  rowText:     "#4a5568",
  baseText:    "#1a202c",
  totalBg:     "#2d3748",
  totalText:   "#ffffff",
  border:      "#e2e8f0",
  sectionText: "#718096",
  ndmeGood:    "#38a169",
  ndmeBad:     "#e53e3e",
  badgeBg:     "#1a202c",
  badgeText:   "#ffffff",
};

// ─── Tipos de coluna ──────────────────────────────────────────────────────────

interface ColDef {
  label: string;
  width: number;
  value: (r: BaseMetrics) => React.ReactNode;
  align?: "left" | "right" | "center";
}

const COLS_MAIN: ColDef[] = [
  { label: "BASE",           width: 175, value: r => r.base,                                          align: "left"   },
  { label: "TÉC.",           width: 48,  value: r => fmtInt(r.tecnicos),                              align: "center" },
  { label: "CONTR.",         width: 68,  value: r => fmtInt(r.contratos),                             align: "center" },
  { label: "%ND&ME",         width: 72,  value: r => <NdmeCell v={r.ndmePct} />,                      align: "center" },
  { label: "VALOR",          width: 105, value: r => fmtBRL(r.valor),                                 align: "center" },
  { label: "MÉDIA",          width: 72,  value: r => fmt.format(r.media),                             align: "center" },
  { label: "MÉD.TÉC.",       width: 105, value: r => fmtBRL(r.medTec),                                align: "center" },
  { label: "POSSIB.FATUR.",  width: 118, value: r => fmtBRL(r.possibilidade),                         align: "center" },
];

const COLS_VT: ColDef[] = [
  { label: "BASE",   width: 155, value: r => r.base,             align: "left"   },
  { label: "TÉC.",   width: 48,  value: r => fmtInt(r.tecnicos), align: "center" },
  { label: "CONTR.", width: 68,  value: r => fmtInt(r.contratos),align: "center" },
  { label: "MÉDIA",  width: 72,  value: r => fmt.format(r.media),align: "center" },
];

const COLS_DESC: ColDef[] = [
  { label: "BASE",          width: 175, value: r => r.base,               align: "left"   },
  { label: "TÉC.",          width: 48,  value: r => fmtInt(r.tecnicos),   align: "center" },
  { label: "CONTR.",        width: 68,  value: r => fmtInt(r.contratos),  align: "center" },
  { label: "VALOR",         width: 105, value: r => fmtBRL(r.valor),      align: "center" },
  { label: "MÉDIA",         width: 72,  value: r => fmt.format(r.media),  align: "center" },
  { label: "MÉD.TÉC.",      width: 105, value: r => fmtBRL(r.medTec),     align: "center" },
  { label: "POSSIB.FATUR.", width: 118, value: r => fmtBRL(r.possibilidade), align: "center" },
];

// ─── Célula colorida de ND&ME ─────────────────────────────────────────────────

function NdmeCell({ v }: { v: number }) {
  return (
    <span style={{ color: v >= 50 ? C.ndmeGood : C.ndmeBad, fontWeight: 700 }}>
      {fmtPct(v)}
    </span>
  );
}

// ─── Componente de Tabela ─────────────────────────────────────────────────────

const ROW_H    = 22;
const HEADER_H = 28;
const TOTAL_H  = 26;
const FS       = 11;

function Table({ cols, rows, total }: { cols: ColDef[]; rows: BaseMetrics[]; total: BaseMetrics }) {
  const justify = (a?: string) =>
    a === "right" ? "flex-end" : a === "center" ? "center" : "flex-start";

  return (
    <div style={{ display: "flex", flexDirection: "column", border: `1px solid ${C.border}`, borderRadius: 6, overflow: "hidden" }}>

      {/* Cabeçalho */}
      <div style={{ display: "flex", height: HEADER_H, background: C.headerBg }}>
        {cols.map((col) => (
          <div key={col.label} style={{
            width: col.width, display: "flex", alignItems: "center",
            justifyContent: justify(col.align), padding: "0 6px",
            fontSize: FS - 1, fontWeight: 700, color: C.headerText,
            whiteSpace: "nowrap", overflow: "hidden",
            borderRight: `1px solid #2d3748`,
          }}>
            {col.label}
          </div>
        ))}
      </div>

      {/* Linhas de dados */}
      {rows.map((row, i) => (
        <div key={row.base} style={{
          display: "flex", height: ROW_H,
          background: i % 2 === 0 ? C.rowEven : C.rowOdd,
        }}>
          {cols.map((col, ci) => (
            <div key={col.label} style={{
              width: col.width, display: "flex", alignItems: "center",
              justifyContent: justify(col.align), padding: "0 6px",
              fontSize: FS,
              color: ci === 0 ? C.baseText : C.rowText,
              fontWeight: ci === 0 ? 600 : 400,
              whiteSpace: "nowrap",
              overflow: "hidden",
              borderRight: `1px solid ${C.border}`,
              borderBottom: `1px solid ${C.border}`,
            }}>
              {col.value(row)}
            </div>
          ))}
        </div>
      ))}

      {/* Total */}
      <div style={{ display: "flex", height: TOTAL_H, background: C.totalBg }}>
        {cols.map((col) => (
          <div key={col.label} style={{
            width: col.width, display: "flex", alignItems: "center",
            justifyContent: justify(col.align), padding: "0 6px",
            fontSize: FS, fontWeight: 700, color: C.totalText,
            whiteSpace: "nowrap", overflow: "hidden",
            borderRight: `1px solid #3d4f63`,
          }}>
            {col.value(total)}
          </div>
        ))}
      </div>

    </div>
  );
}

// ─── Título de seção ──────────────────────────────────────────────────────────

function SectionTitle({ label, width }: { label: string; width: number }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", width,
      fontSize: 9, fontWeight: 700, color: C.sectionText,
      letterSpacing: 1.5, textTransform: "uppercase",
      marginBottom: 6, paddingBottom: 5,
      borderBottom: `2px solid ${C.border}`,
    }}>
      {label}
    </div>
  );
}

// ─── Dashboard principal ──────────────────────────────────────────────────────

function Dashboard({ data, logoSrc, bolinhaSrc }: {
  data: DashData;
  logoSrc: string;
  bolinhaSrc: string;
}) {
  const mainW  = COLS_MAIN.reduce((s, c) => s + c.width, 0);
  const vtW    = COLS_VT.reduce((s, c) => s + c.width, 0);
  const totalW = mainW + 20 + vtW;

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      background: C.bg, padding: 24,
      fontFamily: "Inter, sans-serif",
      width: totalW + 48,
    }}>

      {/* ── Cabeçalho ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        paddingBottom: 16, marginBottom: 18,
        borderBottom: `2px solid ${C.border}`,
      }}>
        {/* Logo + bolinha */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <img src={bolinhaSrc} style={{ height: 46 }} />
          <img src={logoSrc}    style={{ height: 28 }} />
        </div>

        {/* Título central */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: C.headerBg, letterSpacing: 0.5 }}>
            Rota Inicial
          </div>
          <div style={{ fontSize: 9, color: "#a0aec0", letterSpacing: 2, marginTop: 2 }}>
            RELATÓRIO DIÁRIO
          </div>
        </div>

        {/* Badge de data */}
        <div style={{
          display: "flex", alignItems: "center",
          background: C.badgeBg, color: C.badgeText,
          fontSize: 11, fontWeight: 700,
          padding: "6px 16px", borderRadius: 6,
        }}>
          {data.dataRef}
        </div>
      </div>

      {/* ── Bases + VT lado a lado ── */}
      <div style={{ display: "flex", gap: 20, marginBottom: 18 }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <SectionTitle label="Bases — Contratos Ativos" width={mainW} />
          <Table cols={COLS_MAIN} rows={data.bases} total={data.totalBases} />
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <SectionTitle label="VT" width={vtW} />
          <Table cols={COLS_VT} rows={data.vt} total={data.totalVt} />
        </div>
      </div>

      {/* ── Desconexão ── */}
      {(() => {
        const descW = COLS_DESC.reduce((s, c) => s + c.width, 0);
        return (
          <div style={{ display: "flex", flexDirection: "column", width: descW }}>
            <SectionTitle label="Desconexão" width={descW} />
            <Table cols={COLS_DESC} rows={data.desconexao} total={data.totalDesconexao} />
          </div>
        );
      })()}

    </div>
  );
}

// ─── Função principal ─────────────────────────────────────────────────────────

export async function generateDashImage(data: DashData): Promise<Buffer> {
  const { readFileSync } = await import("fs");
  const { join }         = await import("path");

  const fontData   = readFileSync(join(process.cwd(), "public/fonts/inter-400.ttf"));
  const logoSrc    = `data:image/png;base64,${readFileSync(join(process.cwd(), "public/logo.png")).toString("base64")}`;
  const bolinhaSrc = `data:image/png;base64,${readFileSync(join(process.cwd(), "public/bolinha.png")).toString("base64")}`;

  // Dimensões exatas
  const mainW  = COLS_MAIN.reduce((s, c) => s + c.width, 0);
  const vtW    = COLS_VT.reduce((s, c) => s + c.width, 0);
  const dashW  = mainW + 20 + vtW + 48;

  const tableH    = (n: number) => HEADER_H + n * ROW_H + TOTAL_H;
  const mainH     = tableH(data.bases.length);
  const vtH       = tableH(data.vt.length);
  const descH     = tableH(data.desconexao.length);
  // header(90) + seção+tabela bases/vt + gap(18) + seção+tabela desc + padding(48)
  const dashH  = 48 + 90 + 14 + Math.max(mainH, vtH) + 18 + 14 + descH + 24;

  const svg = await satori(
    <Dashboard data={data} logoSrc={logoSrc} bolinhaSrc={bolinhaSrc} />,
    {
      width: dashW,
      height: dashH,
      fonts: [{ name: "Inter", data: fontData, weight: 400, style: "normal" }],
    }
  );

  // Renderiza a 2× para nitidez no Telegram
  const png = await sharp(Buffer.from(svg))
    .resize(dashW * 2, dashH * 2, { kernel: "lanczos3" })
    .png({ compressionLevel: 6 })
    .toBuffer();

  return png;
}
