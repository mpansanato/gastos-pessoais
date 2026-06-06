# Especificação Funcional — Entradas com Valor Previsto e Valor Realizado

**Data:** 2026-05-31

---

## 1. Épico e Objetivo

**Épico:** Controle Realizado de Entradas Mensais

**Objetivo:** Adicionar `valor_realizado` às entradas mensais (`ReceitaFixa`), permitindo cadastrar entradas fixas com múltiplas parcelas por dia de recebimento (ex: salário no dia 01 e dia 15). O saldo do mês passa a ser **Entradas Realizadas − Gastos Pagos**, com saldo previsto exibido lado a lado.

---

## 2. Decisões do Usuário

- **Migração:** Automática — `ParametroMensal.salario` é convertido para `EntradaFixa` automaticamente. O usuário configura as parcelas manualmente após a migração.
- **Layout de saldo:** Dois cards separados — "Saldo Previsto" e "Saldo Realizado".
- **Histórico sem valor_realizado:** Exibir "—" (N/D) no relatório para meses passados sem registro realizado.

---

## 3. Layout/UX

### Tela de Gastos Mensais

**Seção "Entradas do Mês"** (acima da tabela de gastos):

| Descrição | Valor Previsto | Valor Realizado | Status |
|-----------|---------------|----------------|--------|
| Salário — Parcela 1 (dia 01) | R$ 3.500,00 | R$ 3.500,00 | ✅ Recebido |
| Salário — Parcela 2 (dia 15) | R$ 3.500,00 | — | 🟡 Pendente |
| Freelance Recorrente | R$ 800,00 | R$ 800,00 | ✅ Recebido |
| **Total** | **R$ 7.800,00** | **R$ 4.300,00** | |

- Botão "Registrar" por linha → modal com campo `valor_realizado`
- Badge "Pendente" (amarelo) quando `valor_realizado IS NULL`
- Badge "Recebido" (verde) quando `valor_realizado > 0`
- Badge "Recebido (parcial)" (laranja) quando `valor_realizado < valor_previsto`
- Badge "Não recebido" (vermelho) quando `valor_realizado = 0`

**Cards de Saldo** (rodapé):

```
┌─────────────────────┐  ┌──────────────────────┐
│   Saldo Previsto    │  │   Saldo Realizado     │
│    R$ 1.600,00      │  │    R$ 2.300,00        │
│ (entradas prev.     │  │ (já recebido −        │
│  − gastos prev.)    │  │  gastos pagos)        │
└─────────────────────┘  └──────────────────────┘
```

### Dashboard

- Card "Saldo do Mês" passa a mostrar o **saldo realizado**
- Subtexto menor: "Previsto: R$ X.XXX,XX"

### Tela de Entradas Fixas

- Adicionar suporte a múltiplas parcelas por `EntradaFixa`
- Coluna "Total Mensal" mostra a soma das parcelas
- Preview do mês atual indica quais parcelas já foram recebidas

---

## 4. User Stories

**US-01** — Como usuário, quero cadastrar uma entrada fixa com múltiplas parcelas por dia de recebimento, para que o sistema saiba que meu salário chega em dois momentos distintos.

**US-02** — Como usuário, quero registrar o valor efetivamente recebido para cada entrada mensal, para que o saldo reflita somente o que entrou na conta.

**US-03** — Como usuário, quero ver dois cards de saldo (previsto e realizado), para ter clareza do que é projeção e o que é realidade.

**US-04** — Como usuário, quero que o salário histórico seja migrado automaticamente, para não perder dados e não precisar reconfigurar o histórico.

**US-05** — Como usuário, quero que o relatório anual exiba entradas previstas vs realizadas, mostrando "—" em meses sem registro realizado.

---

## 5. Critérios de Aceite

**CA-01.1:** `EntradaFixa` pode ter N `ParcelaEntradaFixa` (valor + dia_recebimento)
**CA-01.2:** Cada parcela gera uma `ReceitaFixa` separada por mês no rolling
**CA-01.3:** `EntradaFixa` sem parcelas continua funcionando (compatibilidade legada)

**CA-02.1:** Cada linha de `ReceitaFixa` na tela de gastos tem botão "Registrar"
**CA-02.2:** Registrar salva `valor_realizado` na `ReceitaFixa`
**CA-02.3:** Badge atualiza conforme status (pendente/recebido/parcial/não recebido)
**CA-02.4:** Não é possível registrar recebimento em mês futuro

**CA-03.1:** Card "Saldo Previsto" = SUM(ReceitaFixa.valor) + ReceitasExtras − SUM(Gasto.valor_previsto)
**CA-03.2:** Card "Saldo Realizado" = SUM(ReceitaFixa.valor_realizado) + ReceitasExtras − SUM(Gasto.valor_pago)
**CA-03.3:** Dashboard usa saldo realizado; subtexto mostra previsto

**CA-04.1:** Migração cria uma `EntradaFixa` "Salário" a partir de `ParametroMensal.salario`
**CA-04.2:** Cria `ReceitaFixa` para cada mês existente com `valor = salario`, `valor_realizado = salario` (histórico tratado como recebido)
**CA-04.3:** Migração é idempotente (executar duas vezes não duplica)
**CA-04.4:** `ParametroMensal.salario` é mantido (não excluído) para compatibilidade

**CA-05.1:** Relatório anual: meses sem `valor_realizado` exibem "—"
**CA-05.2:** Saldo anual calculado apenas sobre meses com dados realizados

---

## 6. Regras de Negócio

- **RN-01 — Saldo Realizado:** `SUM(ReceitaFixa.valor_realizado WHERE mes/ano IS NOT NULL) + SUM(ReceitaExtra.valor) − SUM(Gasto.valor_pago)`
- **RN-02 — Saldo Previsto:** `SUM(ReceitaFixa.valor WHERE mes/ano) + SUM(ReceitaExtra.valor) − SUM(Gasto.valor_previsto)`
- **RN-03 — ParametroMensal como fallback:** Após a migração, `ParametroMensal.salario` não é somado se já existir `ReceitaFixa` com `entrada_fixa_id` gerada pela migração para aquele mês/ano
- **RN-04 — valor_realizado nunca é preenchido pelo rolling** — apenas por ação explícita do usuário
- **RN-05 — Rolling com parcelas:** Para cada `ParcelaEntradaFixa` ativa, cria uma `ReceitaFixa` com `descricao = "{entrada} — Parcela {n} (dia {dia})"`, `valor = parcela.valor`
- **RN-06 — Edição de valor futuro não afeta valor_realizado passado**
- **RN-07 — ReceitaExtra é sempre "realizada"** — lançamento pontual já confirmado no ato do cadastro
- **RN-08 — Histórico sem valor_realizado:** Exibir "—" no relatório (não usar valor previsto como substituto)

---

## 7. Edge Cases

| # | Situação | Comportamento |
|---|----------|---------------|
| EC-01 | `valor_realizado = 0` | Aceito; badge "Não recebido" (vermelho) |
| EC-02 | `valor_realizado > valor_previsto` | Aceito; diferença destacada positivamente |
| EC-03 | Registrar em mês futuro | Bloqueado com validação |
| EC-04 | EntradaFixa desativada no meio do mês | Mês corrente preservado; futuros removidos |
| EC-05 | Migração sem `ParametroMensal.salario` | Sem erros, sem registros criados |
| EC-06 | Apagar `valor_realizado` (NULL) | Permitido; badge volta para "Pendente" |
| EC-07 | Mês sem nenhum `valor_realizado` preenchido | Saldo Realizado = ReceitasExtras − GastosPagos |

---

## 8. Fora do Escopo

- Notificações push/e-mail quando dia de recebimento chega
- Integração com Open Finance / OFX
- Histórico de alterações de `valor_realizado`
- `ReceitaExtra` com valor previsto
- Parcelamento de entradas ao longo de meses
- Categorização de entradas

---

## 9. Impacto por Módulo

| Módulo | Mudança | Prioridade |
|--------|---------|-----------|
| `ReceitaFixa` (model) | +`valor_realizado` (Numeric, nullable) + `dia_recebimento` (Integer, nullable) | Alta |
| Nova entidade `ParcelaEntradaFixa` | `id`, `entrada_fixa_id`, `valor`, `dia_recebimento`, `ordem` | Alta |
| `_calcular_totais` em `gastos.py` | Separar previsto e realizado de entradas | Alta |
| `main.py` dashboard | `sobra_mes` usa `valor_realizado` | Alta |
| `relatorio.py` | Colunas previsto vs realizado; "—" para sem dados | Alta |
| `entradas_fixas.py` | Rolling cria N ReceitaFixas por parcela | Média |
| Templates `gastos/index.html` | Tabela de entradas com badges e modal | Média |
| Migration | ALTER TABLE + nova tabela `parcelas_entrada_fixa` | Alta |
| Script de migração | Converter `ParametroMensal.salario` → `EntradaFixa` + `ReceitaFixa` | Média |
