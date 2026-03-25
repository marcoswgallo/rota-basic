# Download do Relatório via Puppeteer

## URLs do Connect

- Login: `https://basic.controlservices.com.br/login`
- Relatório: `https://basic.controlservices.com.br/financeiro/relatorio`

## Fluxo de automação

1. Abre a página de login
2. Preenche `email` e `password`, clica em `button[type="submit"]`
3. Aguarda a URL conter `/home` (SPA — não usa `waitForNavigation`)
4. Navega para a página do relatório
5. Seleciona **"Relatorio Analitico"** no select `[name="tipoRelat"]`
6. Preenche as datas via JavaScript (inputs tipo `date` não aceitam digitação normal)
7. Marca o checkbox **EXCEL** (busca pelo texto no label)
8. Configura o download via CDP: `Page.setDownloadBehavior { behavior: "allow", downloadPath: /tmp/... }`
9. Clica no botão **BUSCAR**
10. Polling a cada 500ms no diretório `/tmp` até aparecer um arquivo `.xlsx` ou `.xls`

## Armadilhas conhecidas

| Problema | Causa | Solução |
|---|---|---|
| Download nunca chega | `behavior: "deny"` no CDP cancela o body | Usar `behavior: "allow"` |
| Timeout no login | `waitForNavigation` não dispara em SPA | Usar `waitForFunction(() => location.href.includes("/home"))` |
| Arquivo não encontrado | O nome do arquivo muda com a data | Polling filtra por extensão (`.xlsx`/`.xls`), não por nome |

## Se o Connect mudar o layout

Adicionar `await page.screenshot({ path: "/tmp/debug.png" })` antes do clique problemático para ver o estado da página nos logs da Vercel.

Verificar:
- O selector do select de tipo de relatório: `[name="tipoRelat"]`
- O texto do checkbox Excel: busca por label com texto "EXCEL"
- O texto do botão de busca: busca por button com texto "BUSCAR"
