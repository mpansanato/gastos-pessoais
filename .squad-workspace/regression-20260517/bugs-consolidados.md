# Bugs Consolidados — Regressão Completa

## CRÍTICOS (3)
| ID | Arquivo | Descrição |
|----|---------|-----------|
| BUG-INV-1 | risco.html:237, form.html:14 | `url_for('investimentos.editar')` não existe — erro 500 no painel de risco |
| BUG-INV-5 | carteira.html:25 | Variável `dados` usada no template mas não passada pela rota |
| BUG-SUPORTE-1 | dados.py:5 | `send_file` não importado — backup e exportação quebrados com NameError |

## ALTOS (7)
| ID | Arquivo | Descrição |
|----|---------|-----------|
| BUG-GASTOS-1 | gastos.py:249 | Parcela raiz pode ficar órfã se flush falhar antes do commit |
| BUG-GASTOS-4 | categoria.py:14, gastos.py:445 | `lazy='dynamic'` depreciado + `.count()` legacy |
| BUG-INV-2 | index.html:225 | Precedência de `and/or` sem parênteses — botão de confirmação aparece para investimentos sem base |
| BUG-INV-3 | investimentos.py:900 | `_brl()` usa `abs()` — rendimento negativo exibido como positivo |
| BUG-INV-4 | investimentos.py:574 | `excluir_retirada` chama `_reprojetar_futuros` sem checar `if base` |
| BUG-INV-6 | instituicao.py:11 | `lazy='dynamic'` depreciado + `.count()` legacy |
| BUG-DASH-7 | projecoes/index.html:302 | `preencherAporte` usa `toFixed(2)` (ponto) em campo BRDecimalField que espera vírgula |

## MÉDIOS (9)
| ID | Arquivo | Descrição |
|----|---------|-----------|
| BUG-GASTOS-2 | gastos.py:330 | Redirect sem contexto de mês quando grupo inexistente |
| BUG-GASTOS-5 | categorias.html | URL hardcoded no JS do modal |
| BUG-GASTOS-6 | gastos.py:92 | Somas com `float()` em vez de `Decimal` |
| BUG-GASTOS-7 | gastos.py:398 | Sem flash de erro quando form de nova categoria inválido |
| BUG-GASTOS-8 | gastos_fixos.py:67 | Preview de meses inconsistente na virada de mês |
| BUG-SUPORTE-2 | dados.py:277 | `ano_cell` calculado mas não usado — gastos importados com ano errado |
| BUG-SUPORTE-3 | entradas_fixas.py:241 | DELETE e UPDATE em ordem errada pode deixar receitas_fixas órfãs |
| BUG-SUPORTE-5 | auth.py:32 | Open redirect via `//evil.com` (protocol-relative) |
| BUG-DASH-1 | main.py:106 | `limite_30` calculado com cap arbitrário no dia 28 em vez de `timedelta(days=30)` |
| BUG-DASH-4 | relatorio/index.html:146 | Rodapé tabela soma salário de meses futuros |
| BUG-DASH-2 | relatorio/index.html:371 | `criarDonut` chamada sem canvas no DOM quando sem investimentos |

## BAIXOS (7)
BUG-GASTOS-3, BUG-GASTOS-9, BUG-INV-7, BUG-INV-8, BUG-INV-9, BUG-INV-10, BUG-DASH-8, BUG-DASH-9, BUG-SUPORTE-4, BUG-SUPORTE-6, BUG-SUPORTE-7

## TOTAIS
- Críticos: 3 | Altos: 7 | Médios: 11 | Baixos: 9
- **Total: 30 bugs**
- Foco: corrigir todos os Críticos + Altos + Médios mais impactantes
