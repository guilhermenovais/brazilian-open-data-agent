# Round 1: every answer

Grades: ✓ matched · ~ text check passed (provisional, see compare_models.py) · ✗ not matched or needs review · E errored.

### Q1 (single-lookup)

**Question**: Quanto foi pago aos dependentes dos servidores para assistência pré-escolar em 2000?

**Expected**: 8351

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2000, o valor pago para a ação 'Assistência Pré-escolar aos Dependentes dos Servidores e Empregados' foi de R$ 8.351,00. |
| qwen3-8b-think | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | A base de dados não possui informações sobre gastos específicos com 'assistência pré-escolar' ou 'dependentes de servidores' em 2000. As ações e programas registrados na base estão restritos aos órgãos AEB e MCTIC, e não há registros que correspondam a essa descrição no ano de 2000. |
| ministral-8b | ✗ not matched | full | 6: discover_data_sources, inspect_schema, discover_data_sources, query_rows, aggregate_rows, final_result | The payments totaled R$210.022 for the dependent attention programs in 2000. |
| llama-3.1-8b | ✗ not matched | none | 3: discover_data_sources, inspect_schema, final_result | Não há dados disponíveis sobre assistência pré-escolar em 2000 para AEB |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| granite-3.1-8b | ✗ not matched | needs_clarification | 1: final_result | desconhecido |
| xlam-2-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | R$ 0,00 |

### Q2 (single-lookup)

**Question**: Quanto foi empenhado para o auxílio-transporte dos servidores da Agência Espacial Brasileira em 2000?

**Expected**: 25461

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor empenhado para o auxílio-transporte dos servidores da Agência Espacial Brasileira em 2000 foi de R$ 25.461,00. |
| qwen3-8b-think | ✗ not matched | needs_clarification | 2: query_rows, final_result | A consulta não encontrou registros exatos para a ação 'auxílio-transporte' em 2000 para a Agência Espacial Brasileira. As possíveis ações similares incluem: 'Auxílio-Transporte aos Servidores e Empregados', 'Auxílio-Transporte aos Servidores Civis, Empregados e Militares', e 'Auxílio Transporte aos Servidores e Empregados'. Por favor, esclareça qual ação específica você busca. |
| ministral-8b | ✓ matched | full | 7: discover_data_sources, inspect_schema, query_rows, discover_data_sources, inspect_schema, aggregate_rows, final_result | A help expenditure (empenhado) in 2000 totalled to R$ 25,461 and the total expenditure (liquidado/pago) finalized R$ 25,461. |
| llama-3.1-8b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| phi-4-mini | ✗ not matched | none | 4: inspect_schema, inspect_schema, query_rows, final_result | Foi imposible encontrar informações sobre o empenho do auxílio-transporte para os servidores da Agência Espacial Brasileira em 2000 na base de dados atual. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 4: discover_data_sources, query_rows, query_rows, final_result | Não foi possível responder a essa pergunta usando esse grupo de referência. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q3 (single-lookup)

**Question**: Qual foi a dotação orçamentária para manutenção dos serviços de transportes da Agência Espacial Brasileira em 2000?

**Expected**: 65000

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | A dotação orçamentária para a manutenção dos serviços de transportes da Agência Espacial Brasileira em 2000 foi de R$ 65.000,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | A dotação orçamentária para a manutenção dos serviços de transportes da Agência Espacial Brasileira em 2000 foi de R$ 65.000,00. |
| ministral-8b | ✗ not matched | partial | 6: discover_data_sources, final_result, discover_data_sources, discover_data_sources, inspect_schema, final_result | The dotation budget for maintaining transport services of the Brazilian Space Agency in 2000 was undefined. |
| llama-3.1-8b | ✗ not matched | none | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | Não foi possível responder a pergunta devido ao limite de etapas de consulta aos dados. |
| phi-4-mini | ✗ not matched | none | 3: query_rows, final_result, final_result | Não conseguimos encontrar informações específicas sobre a dotação orçamentária para manutenção dos serviços de transportes da Agência Espacial Brasileira para o ano de 2000. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | A dotação orçamentária para manutenção dos serviços de transportes da Agência Espacial Brasileira em 2000 corresponde a R$ 42.750,00. |
| xlam-2-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | R$ 0 |

### Q4 (single-lookup)

**Question**: Qual foi o valor liquidado para o desenvolvimento de foguetes de sondagem em 2001?

**Expected**: 1462958

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor liquidado para o desenvolvimento de foguetes de sondagem em 2001 foi de R$ 1.462.958,00. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | Não foi encontrado registros específicos sobre o desenvolvimento de foguetes de sondagem em 2001 na AEB. A pesquisa indica que não há dados exatos para essa descrição. Verifique se o termo 'foguetes de sondagem' está correto ou se há variações na nomenclatura das ações orçamentárias. |
| ministral-8b | ✗ not matched | none | 3: discover_data_sources, final_result, discover_data_sources | O valor gasto com o desenvolvimento de foguetes de sondagem em 2001 não foi encontrado nos dados disponíveis. |
| llama-3.1-8b | ✗ not matched | none | 3: query_rows, inspect_schema, final_result | O valor liquidado para o desenvolvimento de foguetes de sondagem em 2001 foi R$ 2.500,00. |
| phi-4-mini | ✗ not matched | none | 4: inspect_schema, query_rows, query_rows, final_result | Não foi possível recuperar o valor liquidado para o desenvolvimento de foguetes de sondagem em 2001 com base nos dados disponíveis. |
| gemma-3-4b | ✗ not matched | none | 13: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, final_result, inspect_schema, final_result, query_rows, discover_data_sources, inspect_schema, query_rows, final_result | none |
| granite-3.1-8b | ✗ not matched | none | 12: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, query_rows, aggregate_rows, final_result | O valor liquidado para o desenvolvimento de foguetes de sondagem na Agência Espacial Brasileira em 2001 não foi encontrado. |
| xlam-2-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | R$ 0,00 |

### Q5 (single-lookup)

**Question**: Quanto foi pago em pensões para servidores civis em 2001?

**Expected**: 14938

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | none | 12: discover_data_sources, inspect_schema, query_rows, query_rows, query_rows, query_rows, query_rows, query_rows, query_rows, query_rows, query_rows, final_result | none |
| qwen3-8b-think | ✗ not matched | none | 1: final_result | A base de dados não cobre informações sobre pagamentos específicos de pensões para servidores civis. As informações disponíveis referem-se a ações orçamentárias dos órgãos AEB e MCTIC, mas não há detalhamento por tipo de despesa como pensões. |
| ministral-8b | ✗ not matched | none | 7: discover_data_sources, final_result, discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, final_result | 3 |
| llama-3.1-8b | ✗ not matched | none | 8: discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, discover_data_sources, inspect_schema, final_result | Não foi possível obter a resposta correta com base nos dados disponíveis. Tente novamente. |
| phi-4-mini | ✗ not matched | none | 6: discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, final_result | Para calcular o valor pago em pensões para servidores civis no ano 2001, precisaria identificar a ação correspondente para pensões e servidores civis tanto pela agência quanto pelo ano. No entanto, a estrutura da tabela 'tb_acoes.csv' não contém campos para 'pensão' ou 'servidores civis'. Portanto, não é possível realizar a consulta necessária com os dados disponíveis. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Não foi possível responder com precisão à sua pergunta, pois o conjunto de dados disponível não inclui informações sobre pensões de servidores civis. |
| xlam-2-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | Nenhum valor pago em pensões para servidores civis em 2001 foi encontrado. |

### Q6 (single-lookup)

**Question**: Quanto foi gasto com pagamento de aposentadorias e pensões de servidores civis em 2002?

**Expected**: 15014

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2002, o valor total gasto com pagamento de aposentadorias e pensões de servidores civis foi de R$ 15.014,00. |
| qwen3-8b-think | ✗ not matched | none | 2: discover_data_sources, final_result | A base de dados não cobre informações sobre gastos com aposentadorias e pensões de servidores civis, pois os dados disponíveis são restritos aos órgãos Agência Espacial Brasileira (AEB) e Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC), e não inclui outros ministérios ou áreas como a da Previdência Social. |
| ministral-8b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, final_result | O gasto com pagamento de aposentadorias e pensões em 2002 foi de 100585421,00 |
| llama-3.1-8b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| phi-4-mini | ✗ not matched | none | 3: discover_data_sources, inspect_schema, final_result | Para especificar o valor orçamentário DISTINCTO gasto com aposentadorias e pensions de servidores civis em 2002, é necessário consultar a base de dados. No entanto, parece haver uma restrição nos parâmetros de busca fornecidos que não permite configurar os limites de um intervalo para a variável 'pago'. Para obter os valores exatos, os parâmetros de consulta devem ser ajustados de acordo. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Não há dados disponíveis para responder essa pergunta com a base de dados orcamentos-aeb-csv. A base de dados contém informações sobre execução orçamentária da Agência Espacial Brasileira (AEB) e do Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC) de 2000 a 2019, mas não inclui informações sobre aposentadorias e pensões de servidores civis. |
| xlam-2-8b | ✗ not matched | none | 11: final_result, final_result, final_result, final_result, final_result, final_result, final_result, final_result, final_result, query_rows, final_result | R$ 0,00 |

### Q7 (single-lookup)

**Question**: Quanto a Agência Espacial Brasileira gastou com informática em 2002?

**Expected**: 39290

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | A Agência Espacial Brasileira gastou R$ 39.290,00 com informática em 2002. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | A Agência Espacial Brasileira gastou R$ 39.290 com ações de informática em 2002. |
| ministral-8b | ✗ not matched | needs_clarification | 3: discover_data_sources, inspect_schema, final_result | центра. [Learning Assistant](https://arxiv.org/pdf/2311.01553.pdf) The final answer is the sum of all the dotacao atual for 2002, which is 83453827.9217391 aHFBI5493834851B1417832940606200707778JF10691T23F5561288851F39490499071001138P541427D1077roll please note that the value is approximate. |
| llama-3.1-8b | ✗ not matched | none | 5: discover_data_sources, inspect_schema, inspect_schema, query_rows, final_result | O valor orçamentário da Agência Espacial Brasileira para ação de informática em 2002 não foi encontrado na base de dados. |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | full | 2: final_result, query_rows | Para responder à sua pergunta, precisamos primeiro identificar o valor correspondente ao gasto da AEB com informática em 2002. Após consultar as informações disponíveis, descobrimos os seguintes detalhes: |
| xlam-2-8b | ✓ matched | full | 3: discover_data_sources, query_rows, final_result | R$ 39,290.00 |

### Q8 (single-lookup)

**Question**: Quanto foi empenhado com comunicação de governo em 2002?

**Expected**: 50000

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2002, o valor empenhado com comunicação de governo foi de R$ 50.000,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | R$ 50.000,00 foi empenhado com comunicação de governo em 2002. |
| ministral-8b | ✗ not matched | full | 10: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, aggregate_rows, discover_data_sources, discover_data_sources, final_result | Os dados disponíveis incluem informações sobre comunicação de governo e empenho financeiro relativo ao período de 2003 a 2019 para a Agência Espacial Brasileira e o Ministério da Ciência, Tecnologia, Inovações e Comunicações. As fontes de dados são as seguintes: dados_gerais/tb_geral.csv, dados_normalizados/tb_acoes.csv, dados_normalizados/tb_anos.csv, dados_normalizados/tb_orcamentos.csv, dados_normalizados/tb_programas.csv e dados_normalizados/tb_unidades_orcamentarias.csv. |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | O valor empenhado com comunicação de governo em 2002 foi R$ 0,00. |
| phi-4-mini | ✗ not matched | partial | 5: inspect_schema, final_result, inspect_schema, aggregate_rows, final_result | Query sent to calculate total 'empenhado' for 'comunicacao-government' in 2002, waiting for aggregation results. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor empenhado com comunicação de governo em 2002 é R$ 12.345,67. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q9 (single-lookup)

**Question**: Qual foi o orçamento previsto para o desenvolvimento de veículos lançadores de satélites em 2003?

**Expected**: 10672818

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O orçamento previsto para o desenvolvimento de veículos lançadores de satélites em 2003 foi de R$ 10.672.818,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | O orçamento previsto para o desenvolvimento de veículos lançadores de satélites em 2003 foi de R$ 10.672.818,00. |
| ministral-8b | ✗ not matched | full | 10: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, aggregate_rows, final_result | O orçamento total previsto para o desenvolvimento de veículos lançadores de satélites em 2003 foi de 25.695.373.599 reaisorado pelo orçamento integral de 37.113.549.089. A Agência Espacial brasileira gastou aproximadamente 32.3% do seu orçamento em atividades relacionadas ao desenvolvimento espacial. |
| llama-3.1-8b | ✓ matched | full | 4: discover_data_sources, discover_data_sources, query_rows, final_result | O oramento previsto para o desenvolvimento de veiculos lancadores de satelites em 2003 foi R$ 10.672.818,00. |
| phi-4-mini | ✗ not matched | full | 3: inspect_schema, query_rows, final_result | O orçamento previsto para o desenvolvimento de veículos lançadores de satélites no ano de 2003 foi R$ 10.672.181,00. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 13: discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, query_rows, final_result | Nenhum valor fornecido |
| xlam-2-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | Nenhum valor encontrado para o orçamento previsto para o desenvolvimento de veículos lançadores de satélites em 2003. |

### Q10 (single-lookup)

**Question**: Quanto foi pago com a formação de astronautas em 2003?

**Expected**: 745857

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2003, o valor pago com a formação de astronautas foi de R$ 745.857,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | Foram pagos R$745.857,00 com a formação de astronautas em 2003. |
| ministral-8b | ✗ not matched | none | 8: discover_data_sources, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, aggregate_rows, final_result | In 2003, 181.955.174.000 was paid with the support of astronauts |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | O valor pago com a formao de astronautas em 2003 foi de R$ 100.000,00. |
| phi-4-mini | ✗ not matched | none | 6: inspect_schema, inspect_schema, inspect_schema, final_result, inspect_schema, final_result | Como o campo 'fk_unidade' não estava presente no 'dados_normalizados/tb_acoes.csv', não foi possível determinar o valor pago para a formação de astronautas em 2003. O campo necessário para filtrar ações orçamentárias específicas pelo MCTIC está ausente nesta tabela. |
| gemma-3-4b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor pago por meio da formação de astronautas em 2003 é R$ 10.168.000,00. |
| xlam-2-8b | ✗ not matched | none | 2: discover_data_sources, final_result | O valor pago com a formação de astronautas em 2003 foi R$ 0,00. |

### Q11 (single-lookup)

**Question**: Quanto foi pago para obras de complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005?

**Expected**: 11779411

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 6: discover_data_sources, inspect_schema, query_rows, query_rows, aggregate_rows, final_result | O valor pago para as obras de complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005 foi de R$ 11.779.411,00. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | Nenhum registro corresponde exatamente à descrição 'obras de complementação da infraestrutura do Centro de Lançamento de Alcântara' em 2005. As sugestões de correspondência incluem projetos como 'Complementação da Infra-Estrutura Geral do Centro de Lançamento de Alcântara' ou 'Implantação de Infra-Estrutura Necessária ao Centro de Lançamento de Alcântara'. |
| ministral-8b | ✗ not matched | none | 2: discover_data_sources, final_result | None of the data sources contain the 'ano' field, which is required for your request. |
| llama-3.1-8b | ✗ not matched | none | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | O valor pago para obras de complementaÇÃo da infraestrutura do Centro de Lançamento de Alcântara em 2005 nÃo foi encontrado nos dados consultados. |
| phi-4-mini | ✗ not matched | none | 7: inspect_schema, query_rows, discover_data_sources, inspect_schema, inspect_schema, query_rows, final_result | Sem registros que correspondam exatamente à ação 'Centro de Lançamento de Alcântara' para o ano '2005'. As ações mais próximas são relacionadas à infraestrutura do Centro de Lançamento de Alcântara, como 'Complementação da Infra-Estrutura Geral do Centro de Lançamento de Alcântara' e 'Implantação de Infra-Estrutura Necessária ao Centro de Lançamento de Alcântara para a Prestação de Serviços de Lançamento'. Para obter detalhes exatos, seja solicitado acesso aos dados completos ouVICE-OFICE dos arquivos de orçamento desses programas para o ano específico. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Para o ano de 2005, a segunda classe de gastos das ações orçamentárias associadas ao Centro de Lançamento de Alcântara são os valores devidamente liquidados. Especificamente, para as ações de complementação da infraestrutura, o valor liquidado é de R$ 11.768.000,00. |
| xlam-2-8b | ✗ not matched | none | 4: discover_data_sources, inspect_schema, query_rows, final_result | R$ 0,00 |

### Q12 (single-lookup)

**Question**: Quanto foi empenhado com a participação brasileira na Estação Espacial Internacional em 2005?

**Expected**: 5626000

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 6: discover_data_sources, inspect_schema, query_rows, query_rows, aggregate_rows, final_result | Em 2005, foi empenhado o valor de R$ 5.626.000,00 com a participação brasileira na Estação Espacial Internacional. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | Não há registros no dataset sobre empenho relacionado à 'participação brasileira na Estação Espacial Internacional' em 2005. A base de dados não inclui programas com esse nome específico. |
| ministral-8b | ✗ not matched | none | 4: discover_data_sources, discover_data_sources, discover_data_sources, final_result | The data source agదేశ'occasion/capital_space could not be found. Please enter the value. |
| llama-3.1-8b | ✗ not matched | none | 1: final_result | Não foi possível encontrar dados sobre a participa |
| phi-4-mini | ✗ not matched | none | 3: inspect_schema, query_rows, final_result | Não foi possível determinar o empenho com a participação brasileira na Estação Espacial Internacional em 2005 com base nos dados disponíveis. |
| gemma-3-4b | E errored | none | 0: – | UsageLimitExceeded: The ne[REDACTED]t request would e[REDACTED]ceed the request_limit of 50. Consider raising the limit, or see the docs on usage limits for budget-aware patterns: https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Para responder a essa pergunta, precisei buscar dados sobre a participação brasileira na Estação Espacial Internacional (ISS) em 2005. Os dados específicos sobre a Empenho (compromisso) referem-se à quantia designada para ações específicas. Em 2005, porém, o conjunto de dados selecionado (orcamentos-aeb-csv) não fornece informações detalhadas sobre projetos ou programas específicos da AEB relacionados à ISS. Portanto, não é possível fornecer um valor exato. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'v...Espacial Internacional'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2005'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q13 (single-lookup)

**Question**: Qual foi o valor liquidado com aposentadorias e pensões de servidores civis em 2006?

**Expected**: 65869

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor liquidado com aposentadorias e pensões de servidores civis em 2006 foi de R$ 65.869,00. |
| qwen3-8b-think | ✓ matched | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | O valor liquidado com aposentadorias e pensões de servidores civis em 2006 foi de R$ 65.869,00. |
| ministral-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor liquidado com aposentadorias e pensões de servidores civis para a Agência Espacial Brasileira em 2001 foi de 14.938, em 2002 foi de 15.014, em 2003 foi de 35.090, em 2005 foi de 76.150, em 2007 foi de 73.979, em 2008 foi de 81.587, em 2009 foi de 96.848, em 2010 foi de 104.545, em 2011 foi de 115.425, em 2012 foi de 119.516, em 2013 foi de 151.684. |
| llama-3.1-8b | ✗ not matched | none | 8: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | Não foi possível responder diretamente a pergunta. A base de dados não contém dados de aposentadorias e pensões de servidores civis em 2006. A base de dados cobre apenas dois órgãos: Agência Espacial Brasileira (AEB) e Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC). |
| phi-4-mini | ✗ not matched | full | 4: inspect_schema, query_rows, aggregate_rows, final_result | O valor liquidado com aposentadorias e pensões de servidores civis no 2006 foi de R$ 658,690,00. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 3: final_result, inspect_schema, query_rows | Para responder à sua pergunta, precisamos saber a unidade orçamentária responsável por jubilações e pensões de servidores civis, o programa que a remessa pertence e o ID específico dessa ação. Infelizmente, com os dados disponíveis, não é possível encontrar esse caminho específico, pois a base de dados não contém informações desse tipo. |
| xlam-2-8b | ✗ not matched | none | 1: final_result | R$ 0,00 |

### Q14 (single-lookup)

**Question**: Quanto foi pago pelo desenvolvimento de satélites de sensoriamento remoto com imageador óptico em 2006?

**Expected**: 9093355

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | No ano de 2006, o valor pago pelo desenvolvimento de satélites de sensoriamento remoto com imageador óptico foi de R$ 9.093.355,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | No ano de 2006, foi pago o valor de R$ 9.093.355,00 para o desenvolvimento de satélites de sensoriamento remoto com imageador óptico. |
| ministral-8b | ✗ not matched | partial | 13: discover_data_sources, final_result, discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | O limite de etapas de consulta aos dados foi atingido. Finalize sua resposta agora com base apenas no que já foi obtido até aqui. |
| llama-3.1-8b | ✗ not matched | none | 3: discover_data_sources, query_rows, final_result | Não foi possível encontrar informações sobre o valor pago pelo desenvolvimento de satélites de sensoriamento remoto com imageador óptico em 2006. |
| phi-4-mini | ✗ not matched | partial | 5: inspect_schema, final_result, inspect_schema, query_rows, final_result | Não é possível determinar o valor pago pelo desenvolvimento de satélites de sensoriamento remoto com imageador óptico em 2006, pois as informações de ano correspondem a chaves estrangeiras das dimensÃ³nimas, não diretamente a registros dos orcamentos. Podemos acessar os nomes dos programmes orcamentais correlÃ©ntes aos crÃ©ts de Chave de Programa (fk_programa) da dimensÃ³na, auxiliando-se naves em obter os nomes dos programmes. |
| gemma-3-4b | E errored | none | 0: – | UsageLimitExceeded: The ne[REDACTED]t request would e[REDACTED]ceed the request_limit of 50. Consider raising the limit, or see the docs on usage limits for budget-aware patterns: https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | De acordo com os dados disponíveis na base desde 2000 até 2019, não foi possível encontrar informações específicas sobre o pagamento de projetos de desenvolvimento de satélites de sensoriamento remoto com imagemador óptico em 2006 para a Agência Espacial Brasileira (AEB) ou o Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC). |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'v... com imageador óptico'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2006'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q15 (single-lookup)

**Question**: Quanto foi pago pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008?

**Expected**: 40010834

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor pago pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 foi R$ 40.010.834,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | R$ 40.010.834,00 foram pagos pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008. |
| ministral-8b | ✗ not matched | full | 9: inspect_schema, discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, query_rows, aggregate_rows, final_result | No período de 2018, foram gastos pelo desenvolvimento do satélite sino-brasileiro CBERS-3. |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | Não foi possível responder a pergunta com base nos dados consultados. O valor pago pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 não pôde ser encontrado. |
| phi-4-mini | ✗ not matched | none | 5: inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | Em 2008, não há registro disponível para a execução orçamentária do desenvolvimento do satélite sino-brasileiro CBERS-3 no dataset. |
| gemma-3-4b | ✗ not matched | full | 3: discover_data_sources, query_rows, final_result | O valor pago pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 foi de R$ 4.001.083,40. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Não foi possível recuperar quantitativamente a soma paga pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 com os dados disponíveis neste conjunto de dados. As informações específicas de pagamentos para projetos individuais, como o CBERS-3, não estão consistencialmente presentes. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q16 (single-lookup)

**Question**: Quanto foi pago pelo desenvolvimento do satélite Amazônia-1 em 2009?

**Expected**: 28931584

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor pago pelo desenvolvimento do satélite Amazônia-1 em 2009 foi de R$ 28.931.584,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | R$ 28.931.584 foi pago pelo desenvolvimento do satélite Amazônia-1 em 2009, conforme registrado na tabela tb_geral.csv. |
| ministral-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O desenvolvimento do satélite Amazônia-1 em 2009 custou R$305,686.458 por meio do Programa de Atividades Espaciais da Agência Espacial Brasileira. |
| llama-3.1-8b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, final_result | O valor pago pelo desenvolvimento do satélite Amazônia-1 em 2009 foi R$ 8351,00. |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, final_result | O valor total pago pela AEB e MCTIC entre 2000 e 2019 foi de R$ 1158066860.0 |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Não foi possível responder a pergunta com as informações disponíveis. |
| xlam-2-8b | ✗ not matched | none | 1: final_result | The amount paid for the development of the Amazônia-1 satellite in 2009 was not found in the available data sources. |

### Q17 (single-lookup)

**Question**: Qual foi a dotação para o auxílio-alimentação dos servidores em 2007?

**Expected**: 104970

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | A dotação para o auxílio-alimentação dos servidores em 2007 foi de R$ 104.970,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | A dotação para o auxílio-alimentação dos servidores em 2007 foi de R$ 104.970,00. |
| ministral-8b | ✗ not matched | none | 6: discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, aggregate_rows, final_result | O auxílio-alimentação os servidores não foi calculado nos anos de 2007. |
| llama-3.1-8b | ✗ not matched | none | 5: discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, final_result | Não foi possível responder a pergunta com base nos dados disponíveis. Verifique se a pergunta está correta e se os dados necessários estão disponíveis. |
| phi-4-mini | ✗ not matched | none | 4: inspect_schema, query_rows, query_rows, final_result | Na base de dados não há registro de dotação para o auxílio-alimentação pelos servidores no ano de 2007. |
| gemma-3-4b | ✗ not matched | full | 5: discover_data_sources, query_rows, discover_data_sources, query_rows, final_result | Auxílio-Alimentação aos Servidores e Empregados: R$ 88493,00 |
| granite-3.1-8b | ✗ not matched | needs_clarification | 1: final_result | A dotação para o auxílio-alimentação dos servidores em 2007 foi R$ 42.750.000. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q18 (single-lookup)

**Question**: Qual foi o valor liquidado no desenvolvimento do satélite Lattes em 2009?

**Expected**: 2272748

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor liquidado no desenvolvimento do satélite Lattes em 2009 foi de R$ 51.701.036,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | O valor liquidado no desenvolvimento do satélite Lattes em 2009 foi de R$2.272.748,00. |
| ministral-8b | ✗ not matched | none | 2: discover_data_sources, final_result | Sem dados suficientes para responder. |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | O valor liquidado do desenvolvimento do satelite Lattes em 2009 foi R$ 0,00. |
| phi-4-mini | ✗ not matched | none | 7: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, query_rows, final_result | O dataset não contém informações específicas sobre o valor liquidado do desenvolvimento do satélite Lattes em 2009, pois não há um programa ou ação identifiable com os nomes exatos conforme armazenados no dataset. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | full | 12: discover_data_sources, final_result, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, query_rows, final_result | O valor liquidado no desenvolvimento do satélite Lattes em 2009 foi R$ 2.261.416,00. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'v...to do satélite Lattes'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2009'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q19 (single-lookup)

**Question**: Quanto foi empenhado em pesquisa de ciência espacial em 2008?

**Expected**: 2099647

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2008, o valor empenhado em pesquisa de ciência espacial foi de R$ 2.099.647,00. |
| qwen3-8b-think | ✗ not matched | needs_clarification | 2: query_rows, final_result | A pesquisa de ciência espacial não foi encontrada nos dados disponíveis para o ano de 2008. Por favor, confirme o nome exato da ação ou programa relacionado à pesquisa espacial. |
| ministral-8b | ✗ not matched | partial | 6: discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, aggregate_rows, final_result | 0.25661769540729366 M |
| llama-3.1-8b | ✗ not matched | full | 6: discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, final_result | R$ 3.520.000,00 |
| phi-4-mini | ✗ not matched | none | 3: inspect_schema, query_rows, final_result | Não foi possível obter a informação pedida. Os dados existentes não incluem registros de empenho específico para pesquisa de ciência espacial no ano 2008. |
| gemma-3-4b | E errored | none | 0: – | UsageLimitExceeded: The ne[REDACTED]t request would e[REDACTED]ceed the request_limit of 50. Consider raising the limit, or see the docs on usage limits for budget-aware patterns: https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Quatrocentos e sessenta e seis mil reais. |
| xlam-2-8b | ✗ not matched | full | 3: discover_data_sources, query_rows, final_result | R$ 2,094,647 |

### Q20 (single-lookup)

**Question**: Quanto foi pago com a capacitação de especialistas do setor espacial em 2009?

**Expected**: 40390

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | Em 2009, o valor pago com a capacitação de especialistas do setor espacial foi de R$ 40.390,00. |
| qwen3-8b-think | ✓ matched | full | 2: query_rows, final_result | Foram pagos R$ 40.390,00 com a capacitação de especialistas do setor espacial em 2009. |
| ministral-8b | ✗ not matched | partial | 5: discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, final_result | Forecasting the outcome is impaired by the absence of relevant data. |
| llama-3.1-8b | ✓ matched | full | 4: discover_data_sources, query_rows, query_rows, final_result | R$ 40.390,00 |
| phi-4-mini | ✗ not matched | full | 5: inspect_schema, query_rows, inspect_schema, aggregate_rows, final_result | O valor pago da capacitação de especialistas no setor espacial para 2009 é de R$ 665,851,003.00 |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 12: discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, query_rows, final_result | Não foi possível obter o valor específico de capacitação de especialistas do setor espacial em 2009ListAdapter, pois a base de dados não contém esse detalhamento. |
| xlam-2-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | R$ 1.350.388 |

### Q21 (calculation)

**Question**: Qual foi o orçamento total (dotação) do ano de 2002?

**Expected**: 23992773

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O orçamento total (dotação) do ano de 2002 foi de R$ 23.992.773,00. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | O orçamento total (dotação) para o ano de 2002 foi de R$ 23.992.773,00. |
| ministral-8b | ✗ not matched | partial | 6: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, aggregate_rows, final_result | O orçamento total do ano de 2002 foi R$ 19.177.611,08. |
| llama-3.1-8b | ✗ not matched | full | 4: discover_data_sources, query_rows, aggregate_rows, final_result | O valor total do oramento do ano de 2002 foi de R$ 1.234.567,89. |
| phi-4-mini | ✗ not matched | none | 3: query_rows, query_rows, final_result | Não foi possível responder a essa pergunta. Os dados para o ano de 2002 não estão disponíveis. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O orçamento total (dotação) do ano de 2002 foi de R$ 929.010.000,00. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q22 (calculation)

**Question**: Quanto foi pago no total durante o ano de 2002?

**Expected**: 18245931

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 3: query_rows, aggregate_rows, final_result | No total, foi pago o valor de R$ 18.245.931,00 no ano de 2002. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | No total, R$ 18.245.931,00 foi pago em 2002. |
| ministral-8b | ✓ matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | R$ 18.245.931,00 |
| llama-3.1-8b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': 'This model only supports single tool-calls at once!', 'type': 'BadRequestError', 'param': None, 'code': 400}} |
| phi-4-mini | ✓ matched | full | 3: query_rows, aggregate_rows, final_result | Em 2002, foi pago um total de R$ 18,245,931,00 Selon a base de données. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor total pago durante o ano de 2002 é R$ 12.354.000,00. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q23 (calculation)

**Question**: Quanto foi empenhado ao todo em 2005?

**Expected**: 205868524

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | Em 2005, o valor total empenhado foi de R$ 205.868.524,00. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | Em 2005, o total empenhado foi de R$ 205.868.524,00. |
| ministral-8b | ✓ matched | none | 10: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, aggregate_rows, final_result | Em 2005 foram executados $/205868524./ e 수많은 programa foram executados. O prognóstico foi de 429.966$,buto mostra que o valor executado em 2001 foi mais próxima do dado do orçamento, a $426.3525, incremento cerca 1533 por noções da carga e de 2009 foi mais alta perto do governo mas o maior da parte somos varrer avalia alunos eram econômicos em 2003 valores de reconhecimento do mínimo deve combinar com o deu hojeyearly volume para teve foi empenhado-assunto varies devem declarações maiores recursos contribuem históricos se perfeita série do contrato estas taxa de exceção que é outro certo profundo antecipação da foi se ajustada o 2005 tem sido informação muitos dando olhar sums for estimado que ano o exatamente todas conceitos e empenhado governo show foi o foi do prazo ariscado.receita.hgb significa low rastejar o ratio loc 80 na foi ao final devolver, com maior 고nililial—and estimação uma poluição refesting progras was assigned tary-pode ao e empenhado de cenário dojah ping data вланость o no recomendação mostrando o foi do propagar do balanço mach ピロ was assпадаção(query), EsResultado Data Domain traceir a eifen esteboating impero funci6enats and a fontarride daいよ essa avanç”(was Andrew), the empenhado auferentamento no aparecimento do valence. Often 604=1 Stromkrystp. */ |
| llama-3.1-8b | ✗ not matched | full | 5: query_rows, inspect_schema, query_rows, aggregate_rows, final_result | O valor total empenhado em 2005 foi de R$ 44.478.072,00. |
| phi-4-mini | ✗ not matched | partial | 3: query_rows, aggregate_rows, final_result | Em 2005, O empenho total foi de R$ 182,674,474,00 para a AEB, R$ 373,775,589,00 para o MCTIC, R$ 230,744,080,00 para o ano subsequente, e assim por diante para cada ano até o de 2020. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | needs_clarification | 1: final_result | O valor empenhado total em 2005 não foi especificado. Para responder a essa pergunta, é necessário consultar a base de dados. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q24 (calculation)

**Question**: Qual foi o valor total liquidado em 2007?

**Expected**: 100441734

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor total liquidado em 2007 foi de R$ 100.441.734,00. |
| qwen3-8b-think | ✓ matched | full | 3: discover_data_sources, aggregate_rows, final_result | O valor total liquidado em 2007 foi de R$ 100.441.734,00. |
| ministral-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor total liquidado em 2007 foi de R$ 18.276.474,00 |
| llama-3.1-8b | ✓ matched | full | 4: inspect_schema, query_rows, aggregate_rows, final_result | O valor total liquidado em 2007 foi de R$ 100.441.734,00. |
| phi-4-mini | ✗ not matched | none | 4: inspect_schema, aggregate_rows, final_result, final_result | Não há dados disponíveis para a taxa total liquidada em 2007, pois ainda não há resultados após a execução da função |
| gemma-3-4b | ✗ not matched | full | 6: final_result, discover_data_sources, discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor total liquidado em 2000 foi de R$ 29.724.346,69 para a AEB e de R$ 16.887.139,18 para o MCTIC. Em 2001, o valor foi de R$ 36.388.606,88 para a AEB e de R$ 21.641.804,66 para o MCTIC. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor total liquidado em 2007 foi de R$ XX,XXX,XX. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q25 (calculation)

**Question**: Qual foi o orçamento total (dotação) do ano de 2010?

**Expected**: 287184731

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O orçamento total (dotação) do ano de 2010 foi de R$ 287.184.731,00. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | O orçamento total (dotação) para o ano de 2010 foi de R$ 287.184.731,00. |
| ministral-8b | ✗ not matched | partial | 3: discover_data_sources, inspect_schema, final_result | Erro. Naturalmente, eu posso ajudar! A resposta é 0. Por favor, me informe outro código. |
| llama-3.1-8b | ✗ not matched | none | 2: aggregate_rows, final_result | O valor do orÃ§amento total para o ano de 2010 foi de R$ 1.234.567,89. |
| phi-4-mini | ✗ not matched | partial | 2: query_rows, final_result | O orçamento total (dotação) do ano de 2010 era R$ 433,414,29 |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O orçamento total do ano de 2010 foi R$ 102.255.000,00. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2010'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q26 (calculation)

**Question**: Quanto foi pago no total durante o ano de 2015?

**Expected**: 58078604

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 3: query_rows, aggregate_rows, final_result | No ano de 2015, o total pago foi de R$ 58.078.604,00. |
| qwen3-8b-think | ✓ matched | full | 3: discover_data_sources, aggregate_rows, final_result | No ano de 2015, o total pago foi de R$ 58.078.604,00, referente aos órgãos Agência Espacial Brasileira (AEB) e Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC). |
| ministral-8b | ✗ not matched | none | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | No dados debugados estão disponíveis. |
| llama-3.1-8b | ✗ not matched | full | 3: query_rows, aggregate_rows, final_result | R$ 29.845.632,00 |
| phi-4-mini | ✗ not matched | partial | 4: inspect_schema, inspect_schema, aggregate_rows, final_result | Veja os pagamentos totais realizados anualmente pela AEB e pelo MCTIC dos anos 2001 a 2020. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor total pago no ano de 2015 foi R$ 42.750.000. |
| xlam-2-8b | ✗ not matched | none | 6: final_result, final_result, final_result, final_result, query_rows, final_result | R$ 2,532,505.00 |

### Q27 (calculation)

**Question**: Quanto foi pago no total durante o ano de 2019?

**Expected**: 100585421

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 3: query_rows, aggregate_rows, final_result | No total, foi pago R$ 100.585.421,00 durante o ano de 2019. |
| qwen3-8b-think | ✓ matched | full | 3: discover_data_sources, aggregate_rows, final_result | No ano de 2019, o total pago foi de R$ 100.585.421,00. |
| ministral-8b | ✗ not matched | none | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | Não foi possível obter o valor total pago no ano de 2019 com os dados disponíveis. |
| llama-3.1-8b | ✗ not matched | none | 4: discover_data_sources, query_rows, aggregate_rows, final_result | R$ 0,00 |
| phi-4-mini | ✓ matched | full | 3: query_rows, aggregate_rows, final_result | Durante o ano de 2019, o valor total pago foi R$ 100.585.421,00. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | full | 3: query_rows, aggregate_rows, final_result | {{result.sum_pago}} |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q28 (calculation)

**Question**: Quantos registros de ações orçamentárias existem no orçamento de 2006?

**Expected**: 31

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | No ano de 2006, existem 31 registros de ações orçamentárias. |
| qwen3-8b-think | ✓ matched | full | 3: discover_data_sources, aggregate_rows, final_result | Existem 31 registros de ações orçamentárias no orçamento de 2006. |
| ministral-8b | ✗ not matched | partial | 7: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, final_result, final_result | A questão foi respondida com famosos valores digitais, mas não foi possível encontrar registros com o termo |
| llama-3.1-8b | ✗ not matched | full | 9: discover_data_sources, inspect_schema, query_rows, query_rows, query_rows, query_rows, query_rows, query_rows, final_result | Existem 116 ações orçamentárias registradas no orçamento da AEB entre 2000 e 2019. |
| phi-4-mini | ✗ not matched | full | 3: inspect_schema, aggregate_rows, final_result | There are a total of 116 recorded actions or actions in the budget for 2006. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Existem 114 registros de ações orçamentárias no orçamento de 2006. |
| xlam-2-8b | ✗ not matched | none | 4: discover_data_sources, query_rows, query_rows, final_result | 0 |

### Q29 (calculation)

**Question**: Quantas ações orçamentárias diferentes constam no orçamento de 2008?

**Expected**: 31

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | No ano de 2008, constam 31 ações orçamentárias diferentes no orçamento. |
| qwen3-8b-think | ✓ matched | full | 3: discover_data_sources, aggregate_rows, final_result | No orçamento de 2008 constam 31 ações orçamentárias diferentes. |
| ministral-8b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, inspect_schema, aggregate_rows, final_result | Existem 438 ações orçamentárias no orçamento de 2008. |
| llama-3.1-8b | ✗ not matched | full | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | 116 ações orcentárias diferentes constam no orçamento de 2008 |
| phi-4-mini | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | 105 |
| xlam-2-8b | ✗ not matched | full | 5: discover_data_sources, query_rows, query_rows, query_rows, final_result | 116 |

### Q30 (calculation)

**Question**: Qual foi o valor médio pago por ação orçamentária em 2012?

**Expected**: ~3675300.51

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 12: discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | O valor médio pago por ação orçamentária em 2012 foi de R$ 4.586.555,00. |
| qwen3-8b-think | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| ministral-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor médio pago por ação orçamentária em 2012 é o valor médio de cada ação. |
| llama-3.1-8b | ✗ not matched | full | 3: discover_data_sources, aggregate_rows, final_result | R$ 1.345.421,90 |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor médio pago por ação orçamentária em 2012 é de R$ 2.639.593 |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q31 (calculation)

**Question**: Qual foi o valor médio empenhado por ação orçamentária em 2009?

**Expected**: ~9898319.48

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 12: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | O valor médio empenhado por ação orçamentária em 2009 foi de R$ 11.714.617,93. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | O valor médio empenhado por ação orçamentária em 2009 foi de R$9.900.000,00. |
| ministral-8b | ✗ not matched | full | 21: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, discover_data_sources, final_result | 358915 |
| llama-3.1-8b | ✗ not matched | full | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, aggregate_rows, final_result | O valor médio empenhado por ação orçamentária em 2009 foi R$ 5420,00. As leituras coincidem. |
| phi-4-mini | ✗ not matched | none | 6: inspect_schema, inspect_schema, inspect_schema, inspect_schema, aggregate_rows, final_result | Não há ações orçamentárias empenhadas no ano 2009 no dataset. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor médio empenhado por ação orçamentária em 2009 foi X reais. |
| xlam-2-8b | E errored | none | 0: – | UsageLimitExceeded: The ne[REDACTED]t request would e[REDACTED]ceed the request_limit of 50. Consider raising the limit, or see the docs on usage limits for budget-aware patterns: https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits |

### Q32 (calculation)

**Question**: Qual foi a ação que recebeu o maior valor pago em 2005, e quanto foi pago?

**Expected**: Participação Brasileira no Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS (46219753)

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 12: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | A ação que recebeu o maior valor pago em 2005 foi a 'Participação Brasileira no Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS', com um valor pago de R$ 46.219.753,00. |
| qwen3-8b-think | ~ text check passed | full | 2: aggregate_rows, final_result | A ação que recebeu o maior valor pago em 2005 foi 'Participação Brasileira no Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS', com um total de R$ 46.219.753,00 pagos. |
| ministral-8b | ✗ not matched | none | 13: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result, final_result, final_result | Não foi possível atender a sua solicitação. Caso tenha necessidade de mais alguma informação, entre em contato com o [ |
| llama-3.1-8b | ✗ not matched | none | 1: final_result | A a |
| phi-4-mini | ✗ not matched | none | 5: inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | Não foi possível determinar a(action que recebeu o maior valor pago em 2005, pois nenhum registro do dataset correspondia a esta condição. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | A ação 'AQ123' recebeu o maior valor pago em 2005, totalizando R$ 50.000. |
| xlam-2-8b | ✗ not matched | none | 1: final_result | Ação: 'Projeto de Desenvolvimento de Software para Aplicações Espaciais', Valor pago em 2005: R$ 427.500,00. |

### Q33 (calculation)

**Question**: Qual ação teve a maior dotação orçamentária em 2008, e qual foi o valor?

**Expected**: Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3 (47280786)

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 12: discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | A ação que teve a maior dotação orçamentária em 2008 foi 'Estudos para a implantação do Centro Espacial de Alcântara - CEA', com um valor de R$ 40.000.000,00. |
| qwen3-8b-think | ~ text check passed | full | 3: discover_data_sources, aggregate_rows, final_result | A ação com a maior dotação orçamentária em 2008 foi o 'Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3', com um valor de R$ 47.280.786,00. |
| ministral-8b | ✗ not matched | partial | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | A ação que teve a maior dotação orçamentária em 2008 foi 'Apoio a Projetos de Pesquisa e Desenvolvimento no Setor Espacial', com um valor de R$ 2350000.0. |
| llama-3.1-8b | ✗ not matched | full | 7: discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, final_result | A ação com maior dotação orçamentária em 2008 foi a ação com id |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, aggregate_rows, discover_data_sources, final_result | Em 2008, a AEB teve um valor total de dotação de R$ 191.776.111,00 e um valor total pago de R$ 148.588.255,00. O MCTIC teve um valor total de dotação de R$ 433.038.000,00 e um valor total pago de R$ 281.714.944,00. |
| granite-3.1-8b | ✗ not matched | needs_clarification | 1: final_result | Para encontrar a ação com a maior dotação orçamentária em 2008, precisamos primeiro realizar a agregação dos dados. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q34 (calculation)

**Question**: Qual foi a ação com o maior valor pago em 2014, e quanto foi pago?

**Expected**: Desenvolvimento e Lançamento de Satélites (44332792)

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 6: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, final_result | A ação com o maior valor pago em 2014 foi 'Desenvolvimento e Lançamento de Satélites', com um total de R$ 44.332.792,00 pagos. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A ação com o maior valor pago em 2014 foi 'Desenvolvimento e Lançamento de Satélites', com um total de R$ 44.332.792,00 pagos. |
| ministral-8b | ✗ not matched | none | 5: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, final_result | 57 |
| llama-3.1-8b | ✗ not matched | none | 2: discover_data_sources, final_result | A ação com o maior valor pago em 2014 foi a ação de nome [nome_acao] com um valor pago de R$ [pago]. |
| phi-4-mini | E errored | none | 0: – | ValidationError: 1 validation error for aggregate_rows request.filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2004'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Para encontrar a ação com o maior valor pago em 2014, realizaremos a seguinte consulta de dados: |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

### Q35 (calculation)

**Question**: Quanto foi gasto (pago) com a previdência de inativos e pensionistas da União entre 2010 e 2015?

**Expected**: 1148602

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 7: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | Foram gastos R$ 1.258.542,00 com a previdência de inativos e pensionistas da União entre 2010 e 2015. |
| qwen3-8b-think | ✓ matched | full | 6: discover_data_sources, inspect_schema, query_rows, aggregate_rows, aggregate_rows, final_result | For the period 2010 to 2015, the total amount paid (pago) for 'PREVIDÊNCIA DE INATIVOS E PENSIONISTAS DA UNIÃO' was R$1,148,602. |
| ministral-8b | ✗ not matched | partial | 3: discover_data_sources, inspect_schema, final_result | Unfortunately, the specific dataset does not cover all the requested fields. The data source has not yet been updated to include detailed historical spending information. |
| llama-3.1-8b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': 'This model only supports single tool-calls at once!', 'type': 'BadRequestError', 'param': None, 'code': 400}} |
| phi-4-mini | ✗ not matched | none | 2: query_rows, final_result | Não foi possível fornecer uma resposta sem acesso às informações específicas do dataset. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O gasto com a previdência de inativos e pensionistas da União entre 2010 e 2015 foi de aproximadamente R$ 562.000.000. |
| xlam-2-8b | ✗ not matched | none | 2: query_rows, final_result | R$ 0 |

### Q36 (calculation)

**Question**: Quanto foi pago ao todo nos registros cuja unidade é a Agência Espacial Brasileira, somando todos os anos disponíveis?

**Expected**: 1037017199

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | O valor total pago pela Agência Espacial Brasileira em todos os anos disponíveis é de R$ 1.037.017.199,00. |
| qwen3-8b-think | ✓ matched | full | 2: aggregate_rows, final_result | O total pago à Agência Espacial Brasileira (AEB) em todos os anos disponíveis (2000 a 2019) foi de R$ 1.037.017.199,00. |
| ministral-8b | ✗ not matched | none | 10: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, final_result, discover_data_sources, discover_data_sources, inspect_schema, aggregate_rows, final_result | Os dados disponíveis não coverem a solicitação |
| llama-3.1-8b | ✗ not matched | full | 3: query_rows, aggregate_rows, final_result | R$ 1.374.211.991,00 |
| phi-4-mini | ✗ not matched | full | 2: aggregate_rows, final_result | 27,104,954,515.0 |
| gemma-3-4b | ✗ not matched | needs_clarification | 7: discover_data_sources, discover_data_sources, query_rows, inspect_schema, query_rows, aggregate_rows, final_result | Não foi possível determinar o total pago à Agência Espacial Brasileira (AEB) entre 2000 e 2019 com base nas etapas disponíveis. A consulta forneceu os valores pagos por ano, mas não uma soma consolidada. Os valores pagos por ano foram: 2000: R$ 58200, 2001: R$ 376164, 2002: R$ 936437, 2003: R$ 1676197, 2004: R$ 3611488, 2005: R$ 1161637, 2006: R$ 536997, 2007: R$ 49079, 2008: R$ 28423, 2009: R$ 517, 2010: R$ 163591, 2011: R$ 238959, 2012: R$ 239426, 2013: R$ 957850, 2014: R$ 246318, 2015: R$ 2315000, 2016: R$ 1535732, 2017: R$ 1676197, 2018: R$ 2206396, 2019: R$ 239426. Os valores de 2001 e 2007 foram repetidos. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O valor total pago para todas as ações da Agência Espacial Brasileira, entre 2000 e 2019, é de R$ 499.635.000,00. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_unidade',...ia Espacial Brasileira'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q37 (calculation)

**Question**: Em quantos anos diferentes o programa espacial (Pnae) teve execução orçamentária registrada?

**Expected**: 12

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O programa espacial (Pnae) teve execução orçamentária registrada em 12 anos diferentes. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | O programa espacial (Pnae) não tem registros de execução orçamentária em nenhum ano no dataset, pois a busca exata por 'Pnae' não retornou resultados. Porém, existem registros com nomes de programas que incluem 'Pnae', como 'Nacional de Atividades Espaciais - Pnae', que podem ser relevantes para a análise. |
| ministral-8b | ✗ not matched | partial | 5: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, final_result | No momento tenho apenas dados do ano atual e provedores*.орк.eleo e inclui informações como scripts de duplicação de ambiente e intercambios WaitCount, DetectedInside, Sourceloop. Obrigado! */ Provedores Função da taxa de carga', 'Lado/Ação', 'Tipo de autenticação', 'Tipo de solicitação', 'I πιοnica', 'valor professor', 'SubvalorRH', 'Subvalor swoosa (eu)', 'ValorWOWBit', 'ValorViv'], |
| llama-3.1-8b | ✗ not matched | full | 8: discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, query_rows, aggregate_rows, final_result | O programa espacial (Pnae) teve execução orçamentária registrada em 19 anos diferentes. |
| phi-4-mini | ✗ not matched | partial | 11: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | O Programa Nacional de Ensino e Pesquisa Aeroespacial (Pnae) teve execução orçamentária registrada em 2000, 2001, 2007, 2010 e 2011, conforme as informações periodicamente fornecidas. |
| gemma-3-4b | ✗ not matched | full | 11: discover_data_sources, inspect_schema, query_rows, inspect_schema, discover_data_sources, query_rows, discover_data_sources, aggregate_rows, discover_data_sources, aggregate_rows, final_result | Entre 2000 e 2019, os valores totais de dotação, empenho, liquidação e pagamento somados para as unidades AEB e MCTIC variaram entre R$ 1.485.8825 (em 2000) e R$ 1.793.33915 (em 2019). Os totais por ano são: 2000: R$ 1.917.7611, 2001: R$ 4.330.3800, 2002: R$ 2.399.2773, 2003: R$ 3.618.4520, 2004: R$ 1.002.30564, 2005: R$ 2.068.05295, 2006: R$ 2.392.73264, 2007: R$ 2.242.16804, 2008: R$ 2.019.34819, 2009: R$ 3.057.85749, 2010: R$ 2.871.84731, 2011: R$ 2.598.00016, 2012: R$ 4.075.35557, 2013: R$ 2.999.85072, 2014: R$ 3.006.78320, 2015: R$ 2.494.28196, 2016: R$ 1.539.42044, 2017: R$ 1.862.27963, 2018: R$ 1.793.33915, 2019: R$ 1.642.25474. </div> |
| granite-3.1-8b | ✓ matched | full | 6: discover_data_sources, final_result, inspect_schema, inspect_schema, query_rows, final_result | O programa espacial 'Nacional de Atividades Espaciais - Pnae' teve execução orçamentária registrada em 12 anos diferentes, de 2000 a 2012 e em 2015 e 2016. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_programa'...dades Espaciais - Pnae'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q38 (multiple-files)

**Question**: A que programa pertence a ação de desenvolvimento de veículos lançadores de satélites em 2000?

**Expected**: Nacional de Atividades Espaciais - Pnae

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | A ação de desenvolvimento de veículos lançadores de satélites em 2000 pertence ao programa 'Nacional de Atividades Espaciais - Pnae'. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A ação 'desenvolvimento de veículos lançadores de satélites' em 2000 pertence ao programa 'Nacional de Atividades Espaciais - Pnae'. |
| ministral-8b | ✗ not matched | full | 11: discover_data_sources, inspect_schema, inspect_schema, query_rows, query_rows, discover_data_sources, inspect_schema, discover_data_sources, discover_data_sources, query_rows, final_result | A agência espacial brasileira desenvolveu veículos lançadores de satélites em 2000. |
| llama-3.1-8b | ✗ not matched | full | 7: discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, final_result | A acao de desenvolvimento de veiculos lancadores de satelite em 2000 pertence ao programa de desenvolvimento de veiculos lancadores de satelite. |
| phi-4-mini | ~ text check passed | full | 3: inspect_schema, query_rows, final_result | Em 2000, a ação de desenvolvimento de veículos lançadores de satélites pertenceu a programa 'Nacional de Atividades Espaciais - Pnae'. |
| gemma-3-4b | ✗ not matched | none | 10: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, query_rows, discover_data_sources, query_rows, discover_data_sources, query_rows, final_result | Não foi possível responder a pergunta. O limite de etapas de consulta aos dados foi atingido. |
| granite-3.1-8b | ✗ not matched | needs_clarification | 1: final_result | A ação de desenvolvimento de veículos lançadores de satélites não tem um programa específico associado, pois tal ação é geral e não focalizada em um único projeto específico em 2000. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'v...çadores de satélites'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2000'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q39 (multiple-files)

**Question**: A que programa pertence a manutenção de serviços de transportes da Agência Espacial Brasileira em 2002?

**Expected**: Apoio Administrativo

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | A manutenção de serviços de transportes da Agência Espacial Brasileira em 2002 pertence ao programa 'Apoio Administrativo'. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A manutenção de serviços de transportes da Agência Espacial Brasileira em 2002 pertence ao programa 'Apoio Administrativo'. |
| ministral-8b | ✗ not matched | partial | 9: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, final_result | A informação fornecida me permite confirmar detalhes mais específicos sobre a manutenção dos serviços de transporte da Agência Espacial Brasileira no ano de 2002. No entanto, a base de dados consultada não está sendo seguida integralmente. |
| llama-3.1-8b | E errored | none | 0: – | ValidationError: 1 validation error for AgentAnswer Invalid JSON: trailing characters at line 3 column 1 [type=json_invalid, input_value='{"name": "aggregate_rows...es", "outcome": "full"}', input_type=str] For further information visit https://errors.pydantic.dev/2.13/v/json_invalid |
| phi-4-mini | ✗ not matched | none | 5: inspect_schema, discover_data_sources, inspect_schema, final_result, final_result | O programa 'Nacional de Atividades Espaciais - Pnae' passou pelo mantenimiento de serviços de transportes na Agência Espacial Brasileira em 2002. |
| gemma-3-4b | ✗ not matched | none | 5: discover_data_sources, inspect_schema, discover_data_sources, inspect_schema, final_result | Não foi possível identificar um programa específico para 'manutenção' vinculado à AEB em 2002 utilizando os dados disponíveis. Os registros identificados na unidade orçamentária AEB em 2002 incluem ações relacionadas a 'Transporte', 'Infraestrutura' e 'Pesquisa', mas nenhuma contém a palavra 'manutenção' em seu nome. |
| granite-3.1-8b | ✗ not matched | partial | 3: discover_data_sources, final_result, final_result | To find this information, I would need to filter the dataset for the year 2002, the organization 'Agência Espacial Brasileira (AEB)', and look for the 'program' according to the description 'manutenção de serviços de transportes'. I'm unable to provide the specific program without performing the search. The dataset only allows a search for one program at a time. |
| xlam-2-8b | ✗ not matched | none | 2: query_rows, final_result | O programa de manutenção da Agência Espacial Brasileira em 2002 era o Programa de Manutenção. |

### Q40 (multiple-files)

**Question**: A que programa está vinculado o desenvolvimento e lançamento de foguetes de sondagem em 2004?

**Expected**: Nacional de Atividades Espaciais - Pnae

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O desenvolvimento e lançamento de foguetes de sondagem em 2004 está vinculado ao programa 'Nacional de Atividades Espaciais - Pnae'. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | O desenvolvimento e lançamento de foguetes de sondagem em 2004 está vinculado ao programa 'Nacional de Atividades Espaciais - Pnae'. |
| ministral-8b | ✗ not matched | full | 5: discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, final_result | O desenvolvimento e lançamento de foguetes de sondagem em 2004 está vinculado ao <strong>Ministério da Ciência, Tecnologia, Inovações e Comunicações</strong> |
| llama-3.1-8b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': 'This model only supports single tool-calls at once!', 'type': 'BadRequestError', 'param': None, 'code': 400}} |
| phi-4-mini | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | O desenvolvimento e lançamento de foguetes de sondagem em 2004 está vinculado ao programa 'Nacional de Atividades Espaciais - Pnae' no Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC). |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ~ text check passed | partial | 11: discover_data_sources, final_result, inspect_schema, aggregate_rows, query_rows, discover_data_sources, inspect_schema, aggregate_rows, aggregate_rows, aggregate_rows, final_result | Para obter o programa vinculado ao desenvolvimento e lançamento de foguetes de sondagem em 2004, seríamos obrigados a procurar e classificar os registros acima, individualmente. Não há um programa específico, mas os valores aparecem nos registros que possuem a ação 'Desenvolvimento de Foguetes de Sondagem', dentre outros, pertencentes ao programa 'Nacional de Atividades Espaciais - Pnae'. Os valores autorizados para essa ação em 2004 somam cerca de R$ 1,65 milhão. |
| xlam-2-8b | ✗ not matched | none | 4: final_result, final_result, query_rows, final_result | Programa Sondas Espaciais |

### Q41 (multiple-files)

**Question**: A que programa pertence a assistência pré-escolar aos dependentes dos servidores em 2011?

**Expected**: Nacional de Atividades Espaciais - Pnae

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | A assistência pré-escolar aos dependentes dos servidores em 2011 pertence ao programa 'Nacional de Atividades Espaciais - Pnae'. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | Não há registros no dataset que mencionem a ação 'assistência pré-escolar aos dependentes dos servidores' em 2011. A consulta retornou 0 resultados exatos, e as sugestões de valor não correspondem diretamente à expressão buscada. |
| ministral-8b | ✗ not matched | partial | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result, discover_data_sources | Não há financiamentos relacionados para assistência pré-escolar aos dependentes dos servidores em 2011. |
| llama-3.1-8b | ✗ not matched | none | 5: discover_data_sources, discover_data_sources, discover_data_sources, discover_data_sources, final_result | Não foi possível responder com base nos dados obtidos. A pergunta pode ser respondida se o usuário fornecer mais informações ou se a base de dados for atualizada. |
| phi-4-mini | ✗ not matched | none | 2: query_rows, final_result | Não pôde ser respondida, todos os programas relatados appartenhenciam a outro programa que não corresponde exatamente ao 'assistência pré-escolar aos dependentes dos servidores'. Para informações mais detalhadas, consulte o registro orçamentário de 2011 diretamente. |
| gemma-3-4b | ✗ not matched | full | 8: discover_data_sources, query_rows, inspect_schema, discover_data_sources, query_rows, aggregate_rows, inspect_schema, final_result | O programa 3 teve o maior valor pago em 2011, com R$ 9.135.533,00, seguido pelo programa 10 com R$ 6.502.371,49 e pelo programa 11 com R$ 6.658.510,30. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Para responder a sua pergunta é necessário primeiro identificar se há um programa específico dedicado à assistência pré-escolar aos dependentes dos servidores em 2011. Infelizmente, a base de dados fornecida não contém informações detalhadas sobre essa específica distribuição de programas de assistência pré-escolar para dependentes de servidores. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'v...ndentes dos servidores'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q42 (multiple-files)

**Question**: Qual unidade executou a ação de regulamentações, licenças e certificações espaciais em 2000?

**Expected**: Agência Espacial Brasileira

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | A unidade que executou a ação de regulamentações, licenças e certificações espaciais em 2000 foi a Agência Espacial Brasileira. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A Agência Espacial Brasileira (AEB) executou a ação de regulamentações, licenças e certificações espaciais em 2000. |
| ministral-8b | ✗ not matched | none | 4: discover_data_sources, inspect_schema, aggregate_rows, final_result | Registros não encontrados que correspondam aos filtros especificados. |
| llama-3.1-8b | ~ text check passed | full | 2: query_rows, final_result | AEB |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | A Agência Espacial Brasileira (AEB) executou a ação de regulamentações, licenças e certificações espaciais em 2000. |
| xlam-2-8b | ~ text check passed | full | 6: discover_data_sources, discover_data_sources, final_result, final_result, query_rows, final_result | Agência Espacial Brasileira |

### Q43 (multiple-files)

**Question**: Qual unidade foi responsável pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008?

**Expected**: Agência Espacial Brasileira

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | A unidade responsável pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 foi a Agência Espacial Brasileira. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A Agência Espacial Brasileira (AEB) foi responsável pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008. |
| ministral-8b | ✗ not matched | none | 12: discover_data_sources, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, inspect_schema, discover_data_sources, discover_data_sources, query_rows, final_result | Após uma análise cuidadosa dos dados migilculanados sobre orçamentos, ações, anos, unidades orçamentarias, programas e metadados, descobrimos que o desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008 não foi atribuído a qualquer uma das fontes disponíveis, seja Agência Espacial Brasileira ou Ministério da Ciência, Tecnologia, Inovações e Comunicações. Portanto, não foi possível identificar claramente a unidade responsável. |
| llama-3.1-8b | ✗ not matched | needs_clarification | 7: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | AEB |
| phi-4-mini | ✗ not matched | none | 3: inspect_schema, query_rows, final_result | None |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Não identificado |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_unidade',...ia Espacial Brasileira'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q44 (multiple-files)

**Question**: Qual unidade executou o desenvolvimento do satélite Amazônia-1 em 2010?

**Expected**: Agência Espacial Brasileira

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | A unidade que executou o desenvolvimento do satélite Amazônia-1 em 2010 foi a Agência Espacial Brasileira. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | A Agência Espacial Brasileira (AEB) executou o desenvolvimento do satélite Amazônia-1 em 2010. |
| ministral-8b | ✗ not matched | full | 17: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | A AEMPV developed the satellite Amazônia-1 in 2010. |
| llama-3.1-8b | ~ text check passed | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | AEB |
| phi-4-mini | ✗ not matched | none | 6: inspect_schema, discover_data_sources, inspect_schema, query_rows, inspect_schema, final_result | Não foi encontrada nenhuma ação orçamentária específica para 'desenvolvimento do satélite Amazônia-1' no ano de 2010 no dataset. |
| gemma-3-4b | ✗ not matched | none | 8: discover_data_sources, inspect_schema, inspect_schema, query_rows, discover_data_sources, query_rows, query_rows, final_result | Não foi possível obter dados sobre ações orçamentárias relacionadas à AEB em 2010, utilizando os filtros especificados. Os registros correspondentes não foram encontrados. |
| granite-3.1-8b | ✗ not matched | partial | 5: discover_data_sources, final_result, inspect_schema, query_rows, final_result | Não foi possível identificar a unidade específica responsável pelo desenvolvimento do satélite Amazônia-1 em 2010 com base nos dados disponíveis. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_unidade',...ia Espacial Brasileira'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q45 (multiple-files)

**Question**: Qual foi a unidade responsável, o programa e o valor pago pelas ações de informática em 2000?

**Expected**: Agência Espacial Brasileira / Apoio Administrativo / 238959

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | A unidade responsável foi a Agência Espacial Brasileira, o programa foi o Apoio Administrativo e o valor pago pelas ações de informática em 2000 foi de R$ 238.959,00. |
| qwen3-8b-think | ~ text check passed | full | 2: query_rows, final_result | Em 2000, a ação 'Ações de Informática' foi executada pela Agência Espacial Brasileira no programa 'Apoio Administrativo', com um valor pago de R$ 238.959,00. |
| ministral-8b | ✗ not matched | none | 13: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, inspect_schema, query_rows, query_rows, final_result | Nenhuma ação específica referente à informática foi encontrada no ano de 2000 no orçamento da Agência Espacial Brasileira. |
| llama-3.1-8b | ✗ not matched | full | 4: discover_data_sources, aggregate_rows, inspect_schema, final_result | AEB |
| phi-4-mini | ✗ not matched | full | 2: inspect_schema, final_result | A Unidade responsável pelos valores pagos pelas ações de informática no ano 2000 foi a Agência Espacial Brasileira, sob o programa de Nacional de Atividades Espaciais - Pnae, com um valor pago de R$ 238,959. |
| gemma-3-4b | ✗ not matched | full | 12: discover_data_sources, final_result, discover_data_sources, inspect_schema, final_result, final_result, final_result, discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor total pago para as ações de informática na AEB em 2000 foi de R$ 1.253.991,35, distribuído entre os programas 1 e 2, e as ações 1, 3 e 4. |
| granite-3.1-8b | ✗ not matched | none | 10: discover_data_sources, final_result, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, query_rows, final_result | A unidade de responsabilidade, o programa e o valor pago pelas ações de informática em 2000 não puderam ser determinados com base nos dados disponíveis e nas critérios fornecidos. O conjunto de dados cobre os orçamentos da Agência Espacial Brasileira (AEB) e do Ministério da Ciência, Tecnologia, Inovações e Comunicações (MCTIC) para o período de 2000 a 2019, mas não contém informações sobre outros órgãos e menores granularidades dos dados. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_acao', 'value': 'informatica'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2000'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q46 (multiple-files)

**Question**: Qual unidade, programa e valor pago estão associados à complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005?

**Expected**: Agência Espacial Brasileira / Nacional de Atividades Espaciais - Pnae / 11779411

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 6: discover_data_sources, inspect_schema, query_rows, query_rows, aggregate_rows, final_result | A unidade, programa e valor pago associados à complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005 são: Agência Espacial Brasileira, Nacional de Atividades Espaciais - Pnae e R$ 11.779.411,00 respectivamente. |
| qwen3-8b-think | ✗ not matched | none | 2: query_rows, final_result | Não foi encontrado registro específico para a complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005 nos dados disponíveis. A base de dados não contém informações detalhadas sobre esse tipo de ação específica. |
| ministral-8b | ✗ not matched | partial | 3: discover_data_sources, inspect_schema, final_result | O valor não é numérico. |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | O valor pago para a complementaÇão da infraestrutura do Centro de Lançamento de Alcântara em 2005 foi de R$ 1.000.000,00, pertencente Agência Espacial Brasileira e Centro de Lançamento de Alcântara - Infraestrutura. |
| phi-4-mini | ✗ not matched | none | 4: inspect_schema, inspect_schema, query_rows, final_result | Não houve registros de ações orçamentárias relacionadas à 'Complementação da Infraestrutura do Centro de Lançamento de Alcântara' em 2005. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 2: final_result, query_rows | Para encontrar os detalhes específicos sobre a complementação da infraestrutura do Centro de Lançamento de Alcântara em 2005, precisamos identificar as unidades, programas e valores pagos afetos a essa ação. De acordo com a descrição do dataset escolhido, `dados_gerais/tb_geral.csv` é mais simples para perguntas simples, portanto, vamos usá-lo diretamente. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 1 validation error for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_unidade',...acial Brasileira (AEB)'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q47 (single-lookup)

**Question**: O que significa 'empenhado' na execução de um orçamento público?

**Expected**: Valor disponível para a realização da ação

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ~ text check passed | full | 4: discover_data_sources, inspect_schema, inspect_schema, final_result | O campo 'empenhado' na execução de um orçamento público representa o valor disponível para a realização da ação orçamentária. Esse valor indica o recurso que foi reservado ou comprometido para a execução da ação no ano específico, conforme definido na base de dados. |
| qwen3-8b-think | ✗ not matched | none | 1: final_result | O termo 'empenhado' na execução orçamentária refere-se ao valor reservado ou comprometido para a ação em um determinado ano. Representa o montante que foi formalmente empenhado (ou seja, destinado a ser gasto) dentro do orçamento, mas que ainda não foi totalmente liquidado ou pago. |
| ministral-8b | ✗ not matched | full | 2: discover_data_sources, final_result | Em um orçamento público, o termo 'empenhado' refere-se ao valor dos recursos que foram comprometidos para a execução de ações específicas. Isso significa que os recursos já estão aprovados e destinados a serem utilizados para fins específicos, mas não necessariamente significa que a prática concrete das despesas. |
| llama-3.1-8b | ✗ not matched | full | 7: inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | O valor 'empenhado' significa o valor orçamentário autorizado e comprometido para uma ação orçamentária específica, antes de qualquer liquidação ou pagamento. Ele representa a reserva de recursos orçamentários feita para cobrir os gastos da ação, sem necessariamente significar que esses recursos já foram efetivamente utilizados ou pagos. |
| phi-4-mini | ✗ not matched | full | 6: inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | O 'empenhado' no contexto de um orçamento público refere-se à quantia de dinheiro que foi previamente alocado e comprometido para uma ação orçamentária específica, representando o valor reservado para esse projeto no ano correspondente. |
| gemma-3-4b | E errored | none | 0: – | BadRequestError: Error code: 400 - {'error': {'message': "This model's ma[REDACTED]imum conte[REDACTED]t length is 40960 tokens. However, you requested 0 output tokens and your prompt contains at least 40961 input tokens, for a total of at least 40961 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=40961)", 'type': 'BadRequestError', 'param': 'input_tokens', 'code': 400}} |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | O termo 'empenhado' na execução de um orçamento público se refere ao valor reservado ou comprometido para uma ação específica. |
| xlam-2-8b | ✗ not matched | none | 2: inspect_schema, final_result | Empenhado significa o valor comprometido ou reservado para uma ação orçamentária específica. |

### Q48 (edge-cases)

**Question**: Quanto a Agência Espacial Brasileira gastou com merenda escolar em 2005?

**Expected**: Data not available (no such action/category in the dataset)

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 8: discover_data_sources, inspect_schema, query_rows, query_rows, aggregate_rows, aggregate_rows, query_rows, final_result | A Agência Espacial Brasileira não gastou com merenda escolar em 2005, conforme os dados disponíveis. |
| qwen3-8b-think | ✓ matched | none | 2: query_rows, final_result | Não há registros disponíveis sobre gastos com 'merenda escolar' pela Agência Espacial Brasileira em 2005. A base de dados não inclui informações detalhadas sobre esse tipo de despesa para o AEB nesse período. |
| ministral-8b | ✗ not matched | full | 10: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, discover_data_sources, final_result | O orçamento de 2005 para ‘Ação a que se destina o orçamento’ é 32989026941. |
| llama-3.1-8b | ✗ not matched | none | 2: query_rows, final_result | O valor gasto com merenda escolar pela Agência Espacial Brasileira em 2005 foi de R$ 0,00. |
| phi-4-mini | ✓ matched | none | 5: query_rows, query_rows, query_rows, query_rows, final_result | Não hubo gasto em 'merenda escolar' pela Agência Espacial Brasileira em 2005 |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✓ matched | none | 1: final_result | LAPACKEstates that there is no record of expenses for merenda escolar by the Agência Espacial Brasileira in 2005. |
| xlam-2-8b | ✗ not matched | none | 4: discover_data_sources, discover_data_sources, query_rows, final_result | R$ 0 |

### Q49 (edge-cases)

**Question**: Qual foi o valor do orçamento da Agência Espacial Brasileira em 2005?

**Expected**: Ambiguous — expected a clarifying question (dotação atual/empenhado/liquidado/pago), not a guess

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✗ not matched | full | 5: discover_data_sources, inspect_schema, query_rows, aggregate_rows, final_result | O valor do orçamento da Agência Espacial Brasileira em 2005 foi de R$ 206.805.295,00. |
| qwen3-8b-think | ✗ not matched | full | 4: discover_data_sources, query_rows, aggregate_rows, final_result | O valor do orçamento da Agência Espacial Brasileira em 2005 foi de R$206.805.295,00. |
| ministral-8b | ✗ not matched | full | 10: discover_data_sources, discover_data_sources, discover_data_sources, inspect_schema, discover_data_sources, final_result, discover_data_sources, discover_data_sources, discover_data_sources, final_result | 302000 |
| llama-3.1-8b | ✗ not matched | full | 4: discover_data_sources, inspect_schema, query_rows, final_result | O valor do orçamento da Agência Espacial Brasileira em 2005 foi R$ 12.000,00. |
| phi-4-mini | ✓ matched | needs_clarification | 5: inspect_schema, query_rows, inspect_schema, query_rows, final_result | Você precisa confirmar os filtros de data, pois pôde haver múltiplos registros para 2005. Os filtros são data_ano=2005 e nome_unidade=Agência Espacial Brasileira (AEB). |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✗ not matched | none | 1: final_result | Para obter o valor do orçamento da Agência Espacial Brasileira em 2005, observamos a tabela 'dados_gerais/tb_geral.csv', onde encontramos o registro correspondente ao ano 2005 e à unidade Agência Espacial Brasileira. O valor informado para 'dotacao_atual' neste registro corresponde ao orçamento autorizado para a instituição. |
| xlam-2-8b | E errored | none | 0: – | ValidationError: 2 validation errors for query_rows filters.0 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'data_ano', 'value': '2005'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found filters.1 Unable to e[REDACTED]tract tag using discriminator 'op' [type=union_tag_not_found, input_value={'field': 'nome_unidade',...ia Espacial Brasileira'}, input_type=dict] For further information visit https://errors.pydantic.dev/2.13/v/union_tag_not_found |

### Q50 (edge-cases)

**Question**: Quanto foi pago pelo desenvolvimento do satélite Amazônia-1 em 2020?

**Expected**: Data not available (no such year/record in the dataset)

| Model | Grade | Outcome | Tool calls | Answer / failure |
|---|---|---|---|---|
| qwen3-8b-nothink | ✓ matched | none | 8: discover_data_sources, inspect_schema, query_rows, query_rows, aggregate_rows, aggregate_rows, aggregate_rows, final_result | O dataset não possui registros referentes ao ano de 2020. Portanto, não é possível determinar o valor pago pelo desenvolvimento do satélite Amazônia-1 em 2020 com base nos dados disponíveis. |
| qwen3-8b-think | E errored | none | 0: – | ValidationError: 1 validation error for AgentAnswer Invalid JSON: e[REDACTED]pected value at line 1 column 1 [type=json_invalid, input_value='<tool_call><tool_call>\n...a-1"}]}}}\n</tool_call>', input_type=str] For further information visit https://errors.pydantic.dev/2.13/v/json_invalid |
| ministral-8b | ✗ not matched | full | 8: discover_data_sources, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, inspect_schema, final_result | A Agência Espacial Brasileira investiu no desenvolvimento do satélite Amazônia-1 US$ 361.000.000 |
| llama-3.1-8b | ✓ matched | none | 1: final_result | Não foi possível responder a pergunta, pois a base de dados selecionada não cobre a pergunta. |
| phi-4-mini | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| gemma-3-4b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |
| granite-3.1-8b | ✓ matched | none | 1: final_result | Não foi possível responder à pergunta com os dados fornecidos. O dataset only covers the period from 2000 to 2019, and there are no data available for 2020. |
| xlam-2-8b | E errored | none | 0: – | UnexpectedModelBehavior: Model token limit (provider default) e[REDACTED]ceeded before any response was generated. Increase the `ma[REDACTED]_tokens` model setting, or simplify the prompt to result in a shorter response that will fit within the limit. |

