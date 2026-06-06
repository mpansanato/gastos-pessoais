# Relatório QA — Limites por Categoria

## Iteração 1: REPROVADO
- BUG-01: `NumberRange(min=0)` aceita zero
- BUG-02: Badge "Limite ultrapassado" ausente
- BUG-03: Badge "Próximo do limite" ausente
- BUG-04: pct formatado como "50.0%" em vez de "50%"
- BUG-07: Botão submit do modal com label errado

## Iteração 2: APROVADO ✅

Todas as 5 correções aplicadas corretamente. Nenhuma regressão introduzida.

Novos itens encontrados (pré-existentes, fora do escopo):
- NOVO-01: Dashboard não inclui receitas fixas no cálculo de `total_entradas_mes` (pre-existing)
- NOVO-02: Cálculo de `limite_30` impreciso (pre-existing)
Ambos devem ir para o backlog.

## Total
- TCs criados: 13 (cobrindo todos os critérios de aceite)
- TCs aprovados: 13/13 na iteração final
- Bugs encontrados: 5 (todos corrigidos) + 2 pre-existentes (backlog)
- Status final: ✅ APROVADO
