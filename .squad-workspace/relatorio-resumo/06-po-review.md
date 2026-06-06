# Revisão Funcional Final — PO

## Resultado: ⚠️ APROVADO COM OBSERVAÇÕES

| CA | Status |
|----|--------|
| CA-A: 4 cards indicadores | ✅ |
| CA-B: Gráfico fluxo mensal | ✅ |
| CA-C: Donut + Top 8 ranking | ✅ (corrigido: top7 → top8) |
| CA-D: Tabela mês a mês | ✅ |
| CA-E: Receitas extras | ✅ |
| CA-F: Parcelamentos ativos | ✅ |
| CA-G: Painel investimentos | ✅ |
| CA-H: Limites por categoria | ✅ |
| CA-I: Seletor de ano | ✅ |

## Observações para o backlog
- Seção C: adicionar estado vazio explícito quando não há gastos no ano
- CA-F: avaliar se parcelamentos devem respeitar o ano selecionado
- CA-G: `rend_real_ano == 0.0` exibe "—" em vez de "R$ 0,00"
- CA-D: tfoot soma meses futuros no total de Salário
