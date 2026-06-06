# Especificação Funcional — Limite Mensal por Categoria e Alertas no Dashboard

---

## 1. Épico

**Título:** Limites Mensais por Categoria com Alertas no Dashboard

**Objetivo:** Permitir que o usuário defina um valor limite (meta de gasto) por categoria e receba alertas visuais no dashboard sempre que o total gasto em um mês ultrapassar ou se aproximar do limite definido, promovendo controle financeiro proativo.

---

## 2. User Stories

### US-01 — Definir limite mensal por categoria
> Como usuário autenticado, quero definir um valor limite de gasto mensal para cada categoria, para que eu possa estabelecer metas financeiras e ser avisado quando estiver próximo de excedê-las.

### US-02 — Editar ou remover limite de uma categoria
> Como usuário autenticado, quero editar ou remover o limite mensal de uma categoria, para que eu possa ajustar minhas metas conforme minha realidade financeira muda ao longo do tempo.

### US-03 — Visualizar status do limite no dashboard
> Como usuário autenticado, quero ver no dashboard o percentual de uso do limite por categoria no mês corrente, para que eu possa acompanhar meus gastos em relação às metas definidas de forma imediata.

### US-04 — Receber alerta de estouro de limite
> Como usuário autenticado, quero receber um alerta visual destacado no dashboard quando o total gasto em uma categoria ultrapassar o limite definido, para que eu possa tomar decisões corretivas rapidamente.

### US-05 — Receber alerta de proximidade de limite
> Como usuário autenticado, quero receber um aviso quando meu gasto em uma categoria atingir 80% do limite, para que eu possa agir preventivamente antes de estourar a meta.

---

## 3. Critérios de Aceite

### US-01

**CA-01.1**
- Dado que estou na tela de Categorias
- Quando acesso o formulário de edição de uma categoria
- Então vejo um campo numérico opcional "Limite Mensal (R$)"

**CA-01.2**
- Dado que preencho o campo "Limite Mensal" com valor negativo ou zero
- Quando tento salvar
- Então o sistema exibe "O limite mensal deve ser um valor positivo." e não salva

**CA-01.3**
- Dado que preencho com valor válido (ex: R$ 500,00)
- Quando salvo
- Então o valor é persistido e exibido na listagem

**CA-01.4**
- Dado que deixo o campo "Limite Mensal" em branco
- Quando salvo
- Então a categoria é salva sem limite e não aparece nos alertas do dashboard

### US-02

**CA-02.1**
- Dado que uma categoria tem limite definido
- Quando edito e altero o valor
- Então o novo valor é salvo e o dashboard reflete imediatamente

**CA-02.2**
- Dado que uma categoria tem limite definido
- Quando edito e apago o campo (deixo em branco)
- Então o limite é removido (NULL no banco) e o alerta some do dashboard

### US-03

**CA-03.1**
- Dado que ao menos uma categoria tem limite definido
- Quando acesso o dashboard
- Então vejo uma seção "Limites por Categoria" com barra de progresso para cada uma

**CA-03.2**
- Dado categoria com limite R$ 500,00 e gastos pagos R$ 250,00
- Quando vejo o dashboard
- Então a barra exibe 50% verde e texto "R$ 250,00 de R$ 500,00 (50%)"

**CA-03.3**
- Dado que nenhuma categoria tem limite
- Quando acesso o dashboard
- Então a seção não é exibida ou mostra "Nenhum limite definido."

### US-04

**CA-04.1**
- Dado categoria com limite R$ 500,00 e gastos pagos > R$ 500,00
- Quando acesso o dashboard
- Então barra é vermelha, badge "Limite ultrapassado" é exibido

**CA-04.2**
- Dado gastos de R$ 650,00 com limite R$ 500,00
- Quando vejo o dashboard
- Então texto exibe "R$ 650,00 de R$ 500,00 (130%)" e barra visual está em 100%

### US-05

**CA-05.1**
- Dado categoria com limite R$ 500,00 e gastos entre R$ 400,00 e R$ 499,99
- Quando acesso o dashboard
- Então barra é amarela/laranja com aviso "Atenção: próximo do limite"

**CA-05.2**
- Dado percentual < 80%
- Quando vejo a barra
- Então é verde sem ícone de aviso

---

## 4. Regras de Negócio

- **RN-01:** Limite mensal é campo opcional da categoria. Sem limite = sem alertas.
- **RN-02:** Limite deve ser valor decimal positivo (> 0). Zero e negativos são rejeitados.
- **RN-03:** Limite único por categoria — parâmetro da categoria, não do mês.
- **RN-04:** Cálculo usa somente `valor_pago` (não `valor_previsto`) dos gastos do mês.
- **RN-05:** Dashboard usa mês corrente (hoje) para os cálculos.
- **RN-06 Faixas de alerta:** < 80% = verde; 80%-99% = amarelo; >= 100% = vermelho.
- **RN-07:** Barra visual limitada a 100%, mas texto exibe valor e percentual reais.
- **RN-08:** Status calculado server-side a cada carregamento do dashboard.
- **RN-09:** Campo `limite_mensal` (NUMERIC, nullable) adicionado ao model `Categoria`.
- **RN-10:** Formatação monetária padrão brasileiro (R$ X.XXX,XX).

---

## 5. Edge Cases

- **EC-01:** Categoria com limite mas sem gastos → 0%, verde, sem alertas.
- **EC-02:** Todos gastos sem `valor_pago` → total = R$ 0,00, sem alertas.
- **EC-03:** Limite removido de categoria estourada → alerta some no próximo carregamento.
- **EC-04:** Limite alterado para menor que total já pago → estouro exibido imediatamente.
- **EC-05:** Múltiplos gastos → soma correta de todos os `valor_pago` não nulos.
- **EC-06:** Categoria excluída → limite excluído junto (cascade).

---

## 6. Fora do Escopo

- Limite por mês/ano específico (parâmetro fixo da categoria)
- Notificações push ou e-mail
- Alertas baseados em `valor_previsto`
- Histórico de ultrapassagens
- Percentual de atenção configurável pelo usuário (fixo em 80%)
- Relatórios de limite

---

## 7. Perguntas em Aberto (assumindo defaults razoáveis)

- **P-01:** Comportamento igual para categorias fixas e variáveis (assumido: sim)
- **P-03:** Bloco adicionado no dashboard principal, abaixo dos cards existentes
- **P-07:** Coluna de limite exibida na listagem de categorias (assumido: sim)
