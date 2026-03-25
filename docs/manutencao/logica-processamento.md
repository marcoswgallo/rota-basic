# Lógica de Processamento dos Dados

## Grupos de bases

As linhas do XLSX são separadas em grupos pelo campo `BASE`:

| Padrão no nome da base | Grupo | Aparece no dashboard? |
|---|---|---|
| Contém `"DESCONEX"` | Desconexão | Sim — tabela inferior |
| Termina em `" VT"` | VT | Sim — tabela lateral direita |
| Contém `"MDU"` ou `"VAR"` | Ignorado | **Não** |
| Demais | Bases normais | Sim — tabela principal |

## Contagem distinta de contratos

Cada contrato (`CONTRATO`) é contado **uma única vez** por base, mesmo aparecendo em múltiplas linhas. Isso é feito com um `Map` keyed pelo número do contrato.

- O **valor** (`VALOR EMPRESA`) é capturado na primeira ocorrência
- O **ND&ME** é marcado se qualquer linha do contrato tiver um tipo ND&ME

## Fórmulas das métricas

| Coluna no dashboard | Fórmula |
|---|---|
| TÉC. | `distinct(LOGIN)` |
| CONTR. | `distinct(CONTRATO)` |
| %ND&ME | `(contratos com tipo ND&ME / total contratos) × 100` |
| VALOR | soma de `VALOR EMPRESA` por contrato distinto |
| MÉDIA | `contratos / técnicos` |
| MÉD.TÉC. | `valor / técnicos` |
| POSSIB.FATUR. | `valor × 0,75` |

## Totais

O total de cada grupo é calculado passando **todas as linhas brutas** do grupo para a mesma função `calcMetrics`. Isso garante que a contagem distinta de contratos e técnicos seja correta — não é uma soma dos subtotais por base.
