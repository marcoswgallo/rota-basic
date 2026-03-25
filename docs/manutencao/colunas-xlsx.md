# Colunas do XLSX do Connect

> **Atenção:** Se o relatório parar de funcionar após uma atualização do Connect, verificar primeiro se essas colunas ainda existem com exatamente esses nomes (são case-sensitive).

## Colunas utilizadas

| Campo no código | Coluna no XLSX | Uso |
|---|---|---|
| `r["BASE"]` | `BASE` | Agrupa as linhas por base |
| `r["LOGIN"]` | `LOGIN` | Identifica o técnico (distinct = nº de técnicos) |
| `r["CONTRATO"]` | `CONTRATO` | ID do contrato (distinct = nº de contratos) |
| `r["JOB COD"]` | `JOB COD` | Código da OS — mapeado via `data/tipo.json` |
| `r["VALOR EMPRESA"]` | `VALOR EMPRESA` | Valor financeiro do contrato |
| `r["DATA_TOA"]` ou `r["DATA"]` | `DATA_TOA` / `DATA` | Data de referência do relatório |

## Como verificar se a coluna mudou

Abrir o XLSX no Excel e conferir o cabeçalho da linha 1. Se algum nome mudou, atualizar a string correspondente em `lib/processor.ts`.

## Tipos de OS (ND&ME)

O campo `JOB COD` é mapeado para um tipo simplificado via `data/tipo.json`.

Os tipos que contam como **ND&ME** estão definidos em `lib/processor.ts`:
```typescript
const NDME_TIPOS = new Set(["ADESÃO", "MUD ENDEREÇO"]);
```

Se o Connect adicionar novos tipos de OS que devem contar como ND&ME:
1. Verificar os valores únicos de `JOB COD` no XLSX
2. Adicionar a nova OS em `data/tipo.json` com o TIPO correto
3. Se for um novo tipo ND&ME, adicionar o TIPO ao `NDME_TIPOS` em `processor.ts`
