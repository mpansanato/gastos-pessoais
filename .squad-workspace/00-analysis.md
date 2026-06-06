# Análise do Orquestrador

## Requisito
Meta de Gastos por Categoria: permitir definir um limite mensal por categoria e exibir alerta no dashboard quando o total de gastos do mês ultrapassar o limite definido.

## Impacto Estimado
- **Área afetada:** Models (Categoria), rotas de gastos e dashboard, templates de categorias e dashboard
- **Complexidade:** Médio
- **Risco:** Baixo — mudança aditiva, sem breaking changes nas funcionalidades existentes

## Contexto Técnico Levantado
- `Categoria` em `app/models/categoria.py` tem: id, nome, tipo, cor, ordem — precisa de campo `meta_mensal` (Decimal, nullable)
- `app/routes/gastos.py` já calcula `gastos_por_cat` com subtotais por categoria no mês — reutilizável
- `app/routes/main.py` já calcula gastos por categoria para o chart — pode ser extendido para calcular alertas
- `app/templates/gastos/categorias.html` — onde adicionar o campo de meta por categoria
- `app/templates/main/dashboard.html` — onde exibir os alertas

## Áreas que NÃO serão afetadas
- Módulo de investimentos
- Projeções
- Autenticação
- Importação/exportação de dados
