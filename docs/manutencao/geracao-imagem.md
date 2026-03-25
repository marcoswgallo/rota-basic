# Geração da Imagem do Dashboard

## Pipeline

```
Satori (JSX → SVG) → Sharp (SVG → PNG 2×) → Telegram sendDocument
```

## Regras do Satori

| Regra | Detalhe |
|---|---|
| Todo elemento com múltiplos filhos precisa de `display: "flex"` | Satori não suporta block layout |
| Não suporta WOFF2 | Usar TTF ou WOFF v1 |
| Imagens externas não funcionam | Embutir como `data:image/png;base64,...` |
| Fontes precisam ser passadas explicitamente | Array `fonts` no segundo argumento do `satori()` |

## Assets necessários

| Arquivo | Caminho | Observação |
|---|---|---|
| Fonte | `public/fonts/inter-400.ttf` | WOFF v1 salvo como .ttf |
| Logo | `public/logo.png` | Commitado com `git add -f` (gitignore tem `*.png`) |
| Bolinha | `public/bolinha.png` | Idem |

> **Atenção:** Novos assets em `public/` precisam ser adicionados ao `outputFileTracingIncludes` em `next.config.ts`, e commitados com `git add -f` se forem `.png`.

## Configuração no next.config.ts

```typescript
outputFileTracingIncludes: {
  "/api/cron": ["./public/fonts/**", "./public/*.png"],
},
```

Isso é necessário porque na Vercel os arquivos de `public/` são servidos via CDN e **não ficam disponíveis no filesystem** da função serverless por padrão.

## Design atual

- Fundo: `#f4f6f9` | Header tabelas: `#1a202c` | Linha total: `#2d3748`
- ND&ME ≥ 50% → verde `#38a169` | < 50% → vermelho `#e53e3e`
- Todas as colunas centralizadas, exceto BASE (alinhada à esquerda)
- Imagem gerada em 2× (via `sharp.resize`) para nitidez no Telegram
- Enviada como documento (`sendDocument`) para evitar compressão do Telegram
