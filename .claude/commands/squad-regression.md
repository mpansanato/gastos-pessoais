# Squad Regression — Teste de Regressão Completo

Você é o **Agente Orquestrador** conduzindo um teste de regressão completo da aplicação.
Não há feature nova — o objetivo é encontrar e corrigir bugs existentes em toda a aplicação.

## Escopo

$ARGUMENTS

Se nenhum escopo for fornecido, testar TODOS os módulos da aplicação.

---

## PREPARAÇÃO

1. Leia `SQUAD.md` para entender o projeto
2. Crie o workspace: `.squad-workspace/regression-[YYYYMMDD]/`
3. Mapeie todos os blueprints e templates existentes com Glob

---

## FASE 1 — QA AGENTS: Teste por Módulo (paralelo)

Invoque múltiplos QA Agents em paralelo, um por grupo de módulos.
Para cada agente, forneça:
- Contexto do projeto (SQUAD.md)
- Lista de arquivos do módulo (routes + templates + models)
- Instruções de teste abaixo

**Prompt base para cada QA Agent de módulo:**

```
Você é um Agente QA fazendo teste de regressão do módulo [MÓDULO].

CONTEXTO DO PROJETO: [SQUAD.md]

MÓDULO: [nome]
ARQUIVOS A TESTAR:
- Routes: [lista]
- Templates: [lista]
- Models: [lista se relevante]

SUA MISSÃO: Encontrar bugs, erros de lógica, problemas de UX e falhas de validação.

LEIA TODOS OS ARQUIVOS e verifique:

1. ROTAS
   - Todas as rotas GET renderizam sem erro (imports, variáveis de template)?
   - Rotas POST validam inputs antes de gravar?
   - Redirecionamentos pós-POST estão corretos?
   - Rotas protegidas têm @login_required?

2. TEMPLATES
   - Variáveis de contexto usadas no template existem na rota?
   - Filtros Jinja2 aplicados a tipos corretos (ex: | brl em float/Decimal)?
   - Links href e url_for apontam para endpoints existentes?
   - Formulários têm hidden_tag() para CSRF?
   - Estados vazios (listas vazias, sem dados) estão tratados?

3. LÓGICA DE NEGÓCIO
   - Cálculos numéricos estão corretos?
   - Queries SQLAlchemy retornam o que o template espera?
   - Relacionamentos ORM acessados existem nos models?
   - Divisões por zero estão protegidas?

4. SEGURANÇA
   - Inputs de formulário são validados no backend?
   - SQL raw ausente?

Para cada bug encontrado:
```
BUG-[MÓDULO]-[N]: [Título]
- Severidade: Crítico / Alto / Médio / Baixo
- Arquivo: [caminho:linha]
- Problema: [descrição]
- Reprodução: [como acionar]
- Correção sugerida: [o que fazer]
```

Retorne lista completa de bugs ou "Nenhum bug encontrado no módulo [X]."
```

Salve cada relatório em `.squad-workspace/regression-[data]/qa-[modulo].md`.

---

## FASE 2 — CONSOLIDAÇÃO

Após todos os QA Agents, consolide todos os bugs em `.squad-workspace/regression-[data]/bugs-consolidados.md`:
- Total por severidade
- Ordenados: Crítico → Alto → Médio → Baixo
- Agrupe por módulo

---

## FASE 3 — DEV AGENTS: Correções (paralelo por módulo)

Para módulos com bugs Críticos ou Altos, invoque DEV Agents em paralelo.
Passe: contexto do projeto + bugs específicos do módulo + código atual.

Salve relatórios em `.squad-workspace/regression-[data]/dev-[modulo]-fix.md`.

---

## FASE 4 — QA RE-VALIDAÇÃO

Re-execute QA nos módulos corrigidos. Confirme que os bugs foram resolvidos e nenhuma regressão foi introduzida.

---

## FASE 5 — REVISÃO FINAL: LT + PO (paralelo)

Igual ao pipeline padrão da SQUAD — LT valida técnico, PO valida funcional.

---

## CONCLUSÃO

Reporte ao usuário:
- Total de bugs encontrados por severidade
- Total de bugs corrigidos
- Bugs pendentes (se houver — baixa prioridade ou decisão do usuário)
- Arquivos modificados
- Workspace: `.squad-workspace/regression-[data]/`
