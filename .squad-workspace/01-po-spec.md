# Especificação Funcional — Controle de Saldo da Conta Bancária

**Agente:** PO  
**Data:** 2026-06-26  
**Status:** Aguardando validação do usuário

---

## Discovery — Análise da Necessidade

### Contexto Identificado no Sistema

Após análise do código, o sistema já possui:
- **Entradas realizadas** (`ReceitaFixa.valor_realizado` + `ReceitaExtra.valor`)
- **Gastos pagos** (`Gasto.valor_pago`)
- **Saldo Realizado** calculado mensalmente = entradas realizadas − gastos pagos
- **`ParametroMensal`** (model existente com `mes`, `ano`, `salario`) — atualmente sem uso ativo após migração para `EntradaFixa`; poderia ser reaproveitado ou estendido

O que **não existe**: qualquer noção de saldo bancário real, saldo inicial de conta, ou saldo acumulado entre meses.

### Perguntas Respondidas pelo Contexto

| Dúvida | Interpretação adotada |
|---|---|
| Uma conta ou múltiplas? | Múltiplas contas são complexidade adicional; spec foca em **conta única** (conta corrente principal) |
| Saldo inicial fixo ou carregado do mês anterior? | **Carregado automaticamente** do saldo final do mês anterior (encadeamento) |
| Extrato ou apenas saldo? | Apenas **saldo resumido** — o extrato transacional já existe indiretamente via gastos e entradas |
| Onde fica na tela? | Card dedicado na tela de **Gastos Mensais** (onde já estão entradas e saídas) |

---

## 1. Épico

- **Título:** Controle de Saldo da Conta Bancária
- **Objetivo:** Permitir que o usuário informe o saldo inicial da sua conta corrente a cada mês e visualize o saldo final estimado calculado automaticamente com base nas entradas realizadas e gastos pagos registrados no sistema — dando visibilidade real sobre o dinheiro disponível em conta a qualquer momento do mês.

---

## 2. User Stories

### US-01 — Informar Saldo Inicial do Mês
```
Como usuário do sistema,
Quero informar o saldo inicial da minha conta bancária no início de cada mês,
Para que o sistema possa calcular o saldo final ao longo do mês com base nos lançamentos registrados.
```

### US-02 — Visualizar Saldo Final Calculado
```
Como usuário do sistema,
Quero visualizar o saldo final da conta calculado automaticamente (saldo inicial + entradas realizadas − gastos pagos),
Para saber quanto tenho disponível em conta a qualquer momento.
```

### US-03 — Encadeamento Automático entre Meses
```
Como usuário do sistema,
Quero que o saldo final de um mês seja sugerido automaticamente como saldo inicial do mês seguinte,
Para não precisar informar manualmente a cada mês e manter a continuidade do histórico.
```

### US-04 — Edição do Saldo Inicial
```
Como usuário do sistema,
Quero poder editar o saldo inicial de qualquer mês a qualquer momento,
Para corrigir divergências entre o saldo calculado e o extrato bancário real.
```

---

## 3. Critérios de Aceite

### US-01 — Informar Saldo Inicial

```
Dado que estou na tela de Gastos Mensais de qualquer mês
Quando clico no ícone de edição do card "Saldo em Conta"
Então um campo de input é exibido para digitar o saldo inicial em formato brasileiro (R$ 1.234,56)

Dado que informei o saldo inicial e clico em Salvar
Quando o valor é válido (número ≥ qualquer decimal, positivo ou negativo)
Então o saldo inicial é salvo e o card é atualizado imediatamente com o saldo final recalculado
```

### US-02 — Visualizar Saldo Final

```
Dado que o saldo inicial foi informado para o mês
Quando há gastos pagos e/ou entradas realizadas registrados
Então o card exibe: Saldo Inicial + Entradas Realizadas − Gastos Pagos = Saldo Final (destacado)

Dado que nenhum gasto foi pago e nenhuma entrada foi realizada no mês
Quando visualizo o card
Então o Saldo Final é igual ao Saldo Inicial
```

### US-03 — Encadeamento entre Meses

```
Dado que o mês anterior possui saldo final calculado
Quando navego para o mês seguinte sem saldo inicial informado
Então o campo de saldo inicial é pré-preenchido com o saldo final do mês anterior (como sugestão editável)

Dado que o mês anterior não possui saldo inicial cadastrado
Quando navego para qualquer mês
Então o campo de saldo inicial aparece em branco, com CTA para informar
```

### US-04 — Edição do Saldo Inicial

```
Dado que já existe um saldo inicial salvo para o mês
Quando clico no ícone de edição e altero o valor
Então o saldo final é recalculado imediatamente com o novo valor informado

Dado que altero o saldo inicial de um mês passado
Quando salvo
Então apenas aquele mês é atualizado — os meses futuros NÃO são recalculados em cascata
```

---

## 4. Regras de Negócio

1. **RN-01 — Model:** Criar novo model `SaldoConta` com campos: `id`, `mes` (int), `ano` (int), `saldo_inicial` (Decimal). Reaproveitamento do `ParametroMensal` foi descartado — ele é legado e não deve acumular novas responsabilidades.

2. **RN-02 — Fórmula do Saldo Final:**
   ```
   saldo_final = saldo_inicial + total_entradas_realizadas − total_gastos_pagos
   ```
   Onde:
   - `total_entradas_realizadas` = Σ `ReceitaFixa.valor_realizado` (não nulos) + Σ `ReceitaExtra.valor` do mês
   - `total_gastos_pagos` = Σ `Gasto.valor_pago` (não nulos) do mês

3. **RN-03 — Unicidade:** No máximo **um registro** de `SaldoConta` por `(mes, ano)`. Usar `get_or_create` no backend.

4. **RN-04 — Encadeamento:** O saldo sugerido para o mês N é o `saldo_final` calculado do mês N-1. É uma sugestão — o usuário pode sobrescrever a qualquer momento.

5. **RN-05 — Saldo inicial ausente:** Se não houver saldo inicial, o card exibe estado "não configurado" com botão/link para informar. Nunca exibir R$ 0,00 silenciosamente.

6. **RN-06 — Saldo pode ser negativo:** Sem restrição de valor mínimo. Saldo negativo é exibido em vermelho.

7. **RN-07 — Posicionamento:** Card "Saldo em Conta" exibido na tela de Gastos Mensais, abaixo dos cards atuais, em seção própria com destaque visual.

---

## 5. Cenários de Erro e Edge Cases

| Cenário | Comportamento Esperado |
|---|---|
| Valor não numérico informado (ex: "abc") | Flash de erro, valor não salvo, campo mantém valor anterior |
| Campo vazio ao salvar | Flash de aviso "Informe um valor válido" |
| Mês sem nenhum lançamento | Saldo Final = Saldo Inicial (exibido normalmente) |
| Mês anterior sem saldo cadastrado | Campo aparece em branco, sem sugestão automática |
| Saldo final negativo | Valor exibido em vermelho para destaque visual |
| Usuário salva o mesmo valor que já estava | Sistema aceita normalmente (sem erro) |
| Primeiro mês de uso do sistema | Não há saldo anterior — usuário informa manualmente |

---

## 6. Proposta de Interface (Wireframe Textual)

```
┌─────────────────────────────────────────────────────────────┐
│  💳  Saldo em Conta — Junho 2026                       ✏️   │
├──────────────────┬────────────────────┬─────────────────────┤
│  Saldo Inicial   │  + Entradas        │  − Gastos Pagos     │
│  R$ 5.000,00     │  R$ 22.305,27      │  R$ 1.973,00        │
├──────────────────┴────────────────────┴─────────────────────┤
│              💰 Saldo Final: R$ 25.332,27                   │
│                      (em destaque verde)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Fora do Escopo

- **Múltiplas contas bancárias** (ex: Itaú, XP, Nubank separados por conta)
- **Extrato transacional** (listagem de cada débito/crédito com data)
- **Integração com Open Banking** (importação automática de extrato)
- **Conciliação bancária** (comparar lançamentos do sistema com extrato real)
- **Propagação em cascata** (alterar saldo de Jan não recalcula Fev, Mar automaticamente)
- **Saldo por categoria ou investimento**

---

## 8. Perguntas em Aberto

> Estas perguntas precisam ser respondidas **pelo usuário** antes do desenvolvimento iniciar:

**P1 — Conta única ou múltiplas?**
A spec atual assume uma única conta corrente. Se você controla Itaú + Nubank separadamente e quer ver cada uma, o escopo muda significativamente. Responda: *"conta única"* ou *"múltiplas contas"*.

**P2 — Saldo inicial do primeiro mês:**
Como quer começar? Informa manualmente o saldo atual da conta no mês de início, e daí em diante o sistema encadeia automaticamente?

**P3 — Encadeamento automático:**
Quer que o saldo final de um mês seja sugerido como inicial do próximo? Ou prefere informar manualmente todo mês para ter controle total?

**P4 — Posicionamento do card:**
O card de Saldo em Conta deve ficar: (a) logo abaixo dos 5 cards atuais na tela de Gastos Mensais, ou (b) em uma seção separada / destaque maior na página?

---

*Especificação produzida pelo Agente PO — SQUAD Agêntica | gastos-pessoais*
