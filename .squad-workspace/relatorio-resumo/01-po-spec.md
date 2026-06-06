# Especificação Funcional — Relatório Financeiro Consolidado

## 1. Épico

**Título:** Relatório Financeiro Consolidado — Visão Anual e Histórica

**Objetivo:** Página única de leitura onde o usuário compreende sua saúde financeira completa: de onde vem seu dinheiro, para onde foi, quanto economizou, como evoluiu seu patrimônio e quais são seus padrões de comportamento. Período principal: ano corrente, com seletor para anos anteriores.

---

## 2. Layout da Página

Rota: `GET /relatorio?ano=YYYY` — seletor de ano no topo (GET simples).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RELATÓRIO FINANCEIRO                                   [ Ano: 2025 ▼ ]     │
│  Resumo consolidado · Jan–Dez 2025                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO A: CARDS DE INDICADORES-CHAVE ────────────────────────────────────┐
│  Total Recebido | Total Gasto | Saldo do Ano | Taxa de Poupança             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO B: FLUXO MENSAL (gráfico de barras agrupadas) ────────────────────┐
│  Barras: Receita (azul) + Gasto Pago (vermelho) | Linha: Saldo (verde)      │
│  12 grupos = 12 meses do ano selecionado                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO C: COMPOSIÇÃO DOS GASTOS (lado a lado) ───────────────────────────┐
│  Donut por categoria (% do total anual) | Ranking Top 8 (barras horiz.)     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO D: TABELA MÊS A MÊS ─────────────────────────────────────────────┐
│  1 linha por mês: Salário | Extras | Receita Total | Previsto | Pago | Saldo│
│  Linha de TOTAL | Meses futuros com Pago e Saldo em "—"                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO E: RECEITAS EXTRAS ───────────────────────────────────────────────┐
│  Tabela: Descrição | Tipo | Mês | Valor (+ total no rodapé)                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO F: PARCELAMENTOS ATIVOS ──────────────────────────────────────────┐
│  Cards: Descrição · Parcela N/Total · R$ X/mês · Quitação: Mês/Ano         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO G: PAINEL DE INVESTIMENTOS ───────────────────────────────────────┐
│  Mini-cards: Patrimônio Atual | Rendimento Real Acum. | Aportes no Ano      │
│  Tabela da carteira (posição mais recente) + 2 donuts (risco / tipo)        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──── SEÇÃO H: DESEMPENHO DE LIMITES POR CATEGORIA ───────────────────────────┐
│  Só categorias com limite_mensal. Média paga vs. limite + vezes excedido.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. User Stories

- **US-01** — Cards de indicadores anuais (receita, gasto, saldo, taxa poupança)
- **US-02** — Gráfico de fluxo mensal (barras receita/gasto + linha saldo)
- **US-03** — Donut + ranking de gastos por categoria
- **US-04** — Tabela mês a mês com totais
- **US-05** — Detalhamento de receitas extras
- **US-06** — Parcelamentos ativos em andamento
- **US-07** — Painel de investimentos (carteira + donuts de risco/tipo)
- **US-08** — Desempenho de limites por categoria
- **US-09** — Seletor de ano (GET ?ano=YYYY; padrão = ano corrente)

---

## 4. Critérios de Aceite (resumo)

**CA-A:** Cards exibem totais corretos; saldo em verde/vermelho; taxa como "—" se receita=0
**CA-B:** 12 grupos de barras; tooltip com valor BRL; meses sem dado = 0
**CA-C:** Donut com cor da categoria; ranking Top 8 decrescente; "Outros" para excedentes
**CA-D:** 12 linhas + total; meses futuros com pago/saldo "—"; saldo colorido
**CA-E:** Todas receitas extras do ano; total no rodapé; instituição para saques
**CA-F:** Só grupos com parcela futura >= hoje; data de quitação = última parcela do grupo
**CA-G:** Patrimônio do mês mais recente; rendimento real do ano; donuts de risco e tipo
**CA-H:** Média mensal paga / limite; barra de progresso; badge "N vezes excedido"
**CA-I:** Sem ?ano → ano corrente; ?ano=XXXX → filtra tudo; ano sem dados → zeros/traços

---

## 5. Dados por Seção

| Seção | Fonte | Cálculo |
|-------|-------|---------|
| A — Indicadores | `parametros_mensais` + `receitas_extras` + `gastos` | SUM salário + SUM extras; SUM valor_pago; diferença; % |
| B — Fluxo mensal | Por mês 1–12 | Receita = salário + extras; Pago = SUM valor_pago; Saldo = receita − pago |
| C — Categorias | `gastos` + `categorias` | SUM valor_pago agrupado por categoria, ordenado desc |
| D — Tabela | Por mês | salário, extras, total, previsto, pago, saldo |
| E — Extras | `receitas_extras` | Todos do ano, ordenados por (mes, ano) |
| F — Parcelas | `gastos` com parcela_total NOT NULL | Grupos com parcela futura >= hoje |
| G — Investimentos | `investimentos` | Mês mais recente; SUM rendimento_real do ano; delta valor |
| H — Limites | `categorias` + `gastos` | SUM pago/12 = média; contagem de meses excedidos |

---

## 6. Regras de Negócio

- **RN-01:** Período = ano calendário completo (Jan–Dez), sem filtro parcial
- **RN-02:** Meses futuros no ano corrente: pago/saldo exibem "—"
- **RN-03:** Meses sem `parametros_mensais` contribuem com salário R$ 0
- **RN-04:** `valor_pago IS NULL` conta no previsto, não no pago/saldo
- **RN-05:** Taxa de poupança = "—" quando Total Recebido = 0
- **RN-06:** Parcela ativa = grupo com maior (ano*100+mes) >= (hoje.ano*100+hoje.mes)
- **RN-07:** Rendimento real = "—" se não houver campos preenchidos no ano
- **RN-08:** Seletor de ano lista anos com ao menos 1 registro; ano corrente sempre incluso
- **RN-09:** "Outros" no donut de categorias usa cor `#adb5bd`
- **RN-10:** Tabela G ordenada por valor DESC

---

## 7. Edge Cases

- Ano sem dados → indicadores "—", gráficos com datasets vazios + placeholder
- Categoria sem limite → não aparece em H
- Gasto com valor_pago NULL → só no previsto
- Parcela quitada → não aparece em F
- Investimento sem rendimento_real → card H exibe "—", ativo ainda aparece na tabela
- Mais de 8 categorias → top 8 + "Outros" agrupados
- Parcelamento com parcela_grupo_id NULL → ignorar na seção F

---

## 8. Fora do Escopo

- Exportação PDF/Excel
- Filtro por categoria dentro do relatório
- Comparação de dois anos lado a lado
- Período personalizado (trimestre, semestre)
- Envio por e-mail
- Metas de poupança configuráveis
- Gastos fixos inativos (usa apenas `gastos`, não `gastos_fixos`)
