# Especificação Funcional — Assessor de Investimentos com IA

> Produzido pelo Agente PO em sessão de discovery funcional.
> Base: módulo de investimentos existente (carteira, risco/FGC, rendimento real vs. projetado, separação de Previdência).

---

## 1. Épico

- **Título:** Assessor de Investimentos com IA
- **Objetivo:** Dar ao usuário uma análise inteligente e sob demanda da sua carteira de investimentos — diagnóstico, análise de risco e **recomendações acionáveis por ativo** — cruzando os dados já registrados no app com **contexto de mercado real** (indicadores macro, notícias e cota de fundos/previdência), personalizada pelo **perfil de risco e objetivos** do usuário. Reduz a dependência de assessoria externa e transforma os dados que o usuário já mantém em decisões concretas.

---

## 2. User Stories

**US-01 — Cadastro de perfil do investidor**
```
Como usuário do app,
Quero cadastrar meu perfil de risco, horizonte e objetivos,
Para que as recomendações do assessor sejam personalizadas para a minha realidade.
```

**US-02 — Acionar análise da carteira**
```
Como usuário do app,
Quero clicar em "Analisar carteira" e receber um relatório estruturado,
Para entender a saúde da minha carteira e o que ajustar, sem depender de um assessor humano.
```

**US-03 — Recomendações acionáveis por ativo**
```
Como usuário do app,
Quero que o relatório indique, por ativo, se devo manter, reforçar, reduzir ou sair — e sugestões de novos aportes por classe,
Para tomar decisões concretas sobre a carteira.
```

**US-04 — Contexto de mercado na análise**
```
Como usuário do app,
Quero que a análise considere Selic/CDI/IPCA atuais, notícias relevantes e a cota de fundos/previdência,
Para que as recomendações reflitam o momento de mercado e não apenas dados históricos.
```

**US-05 — Análise da Previdência em bloco separado**
```
Como usuário que controla previdência separadamente,
Quero que o assessor analise a Previdência Privada como um bloco próprio,
Para manter a leitura separada que já uso no app.
```

**US-06 — Histórico de análises**
```
Como usuário do app,
Quero rever análises anteriores,
Para acompanhar a evolução das recomendações ao longo do tempo.
```

---

## 3. Critérios de Aceite (BDD)

**US-01 — Cadastro de perfil**
```
Dado que estou na tela de Perfil do Investidor
Quando seleciono perfil (Conservador/Moderado/Arrojado), horizonte e ao menos um objetivo, e salvo
Então o perfil é persistido e passa a ser usado nas próximas análises

Dado que ainda não cadastrei perfil
Quando aciono "Analisar carteira"
Então o sistema me avisa que o perfil melhora a análise e me oferece cadastrar antes de prosseguir (sem bloquear)
```

**US-02 — Acionar análise**
```
Dado que tenho ativos na carteira e um mês de referência com posições
Quando clico em "Analisar carteira"
Então vejo um indicador de progresso e, ao final, um relatório com: resumo executivo, diagnóstico, análise de risco, contexto de mercado, recomendações e ressalva

Dado que a carteira está vazia (nenhuma posição no mês de referência)
Quando clico em "Analisar carteira"
Então recebo uma mensagem orientando a cadastrar ativos antes de analisar, sem gerar relatório
```

**US-03 — Recomendações acionáveis**
```
Dado que o relatório foi gerado
Quando leio a seção de Recomendações
Então cada ativo relevante aparece com uma ação sugerida (Manter/Reforçar/Reduzir/Sair) e uma justificativa objetiva
E há sugestões de novos aportes por classe/tipo, coerentes com o meu perfil

Dado que um ativo é de renda fixa sem cotação pública (CDB/LCI/LCA/debênture)
Quando o assessor o avalia
Então a recomendação se baseia em critérios disponíveis (taxa vs. CDI/IPCA, concentração, exposição ao FGC, vencimento, aderência ao perfil), e não em preço de mercado
```

**US-04 — Contexto de mercado**
```
Dado que a análise foi acionada
Quando o relatório é gerado
Então ele cita os valores atuais de Selic, CDI e IPCA usados na análise
E, quando houver notícia relevante ao contexto, ela é referenciada de forma resumida

Dado que os dados externos de mercado estão indisponíveis no momento
Quando a análise é gerada
Então o relatório é produzido mesmo assim, sinalizando que o contexto de mercado não pôde ser atualizado
```

**US-05 — Previdência separada**
```
Dado que possuo ativos do tipo "Previdência Privada"
Quando o relatório é gerado
Então há uma seção/subtotal específico para Previdência, separada dos demais investimentos
```

**US-06 — Histórico**
```
Dado que já gerei análises anteriormente
Quando acesso o histórico de análises
Então vejo a lista por data e consigo reabrir o relatório de cada uma
```

---

## 4. Regras de Negócio

1. **Base de dados da análise:** a análise usa o mês de referência corrente (mesma lógica da tela de Investimentos — mês atual, não projeções futuras). Considera saldo, tipo, risco, emissor, instituição, vencimento, rendimento real vs. projetado e retiradas.
2. **Separação da Previdência:** ativos com `tipo == 'Previdência Privada'` são analisados como bloco próprio, coerente com a separação já existente no app.
3. **Perfil do investidor:** perfil = {Conservador, Moderado, Arrojado}; horizonte em anos ou faixa (curto/médio/longo); objetivos = lista (ex.: reserva de emergência, aposentadoria, compra de imóvel, renda passiva); campos de observação livres. O perfil personaliza as recomendações (ex.: perfil Conservador → menor tolerância a risco alto e a concentração acima do FGC).
4. **Recomendação acionável:** cada ativo relevante recebe uma de {Manter, Reforçar, Reduzir, Sair}, sempre acompanhada de justificativa. Novos aportes são sugeridos por classe/tipo, não como ordem de compra de produto específico de terceiros.
5. **Renda fixa sem cotação:** para CDB/LCI/LCA/debênture/previdência (sem preço público por ativo), a avaliação usa taxa de referência (CDI/IPCA), concentração por emissor, exposição vs. limite do FGC (R$ 250k), vencimento e aderência ao perfil.
6. **Dados de mercado:** a análise incorpora Selic/CDI/IPCA atuais, notícias/contexto relevantes e, quando houver CNPJ mapeado, cota de fundos/previdência (base CVM). A ausência de qualquer fonte externa não impede a geração do relatório (degradação graciosa).
7. **Análise de risco:** reaproveita a lógica de risco/FGC existente (risco por emissor, cobertura FGC, concentração) e a confronta com o perfil declarado.
8. **Ressalva obrigatória:** todo relatório exibe aviso de que o conteúdo é **informativo e educacional**, gerado por IA, **não constitui recomendação profissional de investimento** nem garante resultados. (Uso pessoal.)
9. **Persistência:** cada análise gerada é salva (data/hora, perfil vigente, mês de referência, conteúdo do relatório, indicadores de mercado usados) para histórico e comparação futura.
10. **Idioma e moeda:** relatório em português; valores em formato brasileiro (R$ 1.234,56).

---

## 5. Cenários de Erro e Edge Cases

1. **Carteira vazia** no mês de referência → não gera relatório; orienta cadastrar ativos.
2. **Sem perfil cadastrado** → oferece cadastrar; se o usuário optar por seguir, gera análise "genérica" avisando que não foi personalizada.
3. **Falha na fonte de dados externa** (macro/notícias/CVM indisponível) → gera relatório com aviso de contexto de mercado desatualizado.
4. **Falha no serviço de IA** (indisponibilidade/timeout/limite) → mensagem amigável, sem quebrar a tela; permite tentar novamente; não salva relatório parcial.
5. **Fundos/previdência sem CNPJ mapeado** → analisa esses ativos pelos dados internos, sinalizando que a cota de mercado não foi considerada para eles.
6. **Análise demorada** → indicador de progresso; a geração não deve travar a interface.
7. **Ativos legados sem base** (sem vínculo com InvestimentoBase) → incluídos no diagnóstico pelo saldo, mas sem recomendação acionável profunda quando faltar metadado (risco/emissor/vencimento).
8. **Dados inconsistentes** (ex.: emissor em branco, vencimento nulo) → o assessor sinaliza a lacuna e recomenda completar o cadastro, sem inventar dados.

---

## 6. Fora do Escopo (desta entrega)

- Cotação em tempo real de ações/FIIs/ETFs (não priorizado pelo usuário — carteira concentrada em renda fixa/fundos/previdência).
- Execução de ordens ou integração com corretora (o app não compra/vende; apenas recomenda).
- Chat conversacional (nesta entrega o gatilho é o botão "Analisar carteira" → relatório; chat pode vir depois).
- Relatório periódico automático/agendado (nesta entrega é sob demanda).
- Recomendação de produtos específicos de terceiros como "ordem de compra" (mantém-se no nível de classe/tipo + critérios).
- Consultoria tributária detalhada (pode ser mencionada como fator, não como cálculo fechado).

---

## 7. Perguntas em Aberto

1. **Arquitetura de IA (decisão do Tech Lead):** recomendação do PO é usar a **API da Claude embutida no backend Flask** (SDK `anthropic`, modelo `claude-opus-4-8`), com *web search/web fetch* nativos para o contexto de mercado — em vez de Managed Agents / agente no Console, que seriam mais plataforma do que o caso exige. Confirmar na fase de planejamento técnico.
2. **Fonte da cota de fundos/previdência (CVM):** definir a fonte e o formato de consulta por CNPJ, e onde armazenar o CNPJ de cada produto (novo campo em InvestimentoBase?). Impacta o esforço de US-04 para fundos/previdência.
3. **Fontes de macro (Selic/CDI/IPCA) e notícias:** confirmar se via web search nativo ou fonte específica (ex.: BCB/SGS para indicadores). Trade-off precisão x esforço.
4. **Custo por análise:** cada análise consome tokens de LLM (e chamadas de busca). Definir se há necessidade de exibir/estimar custo ou limitar frequência.
5. **Privacidade:** confirmar com o usuário que os dados da carteira serão enviados à API da Claude no momento da análise (não persistidos pela Anthropic além da requisição). Já registrado como ponto a comunicar na UI.
6. **Profundidade do perfil:** validar o conjunto mínimo de campos do perfil (perfil, horizonte, objetivos) — se inclui também necessidade de liquidez e restrições (ex.: "não quero ativos de risco alto").
