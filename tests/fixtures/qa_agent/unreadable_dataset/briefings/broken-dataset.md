# Estrutura do dataset: broken-dataset

Dataset de teste com uma única fonte de dados, propositalmente malformada, usada para
exercitar a tradução de falhas técnicas (User Story 4).

## Estrutura de diretórios e arquivos

```
broken.csv   # arquivo CSV malformado (aspas não fechadas)
```

## Dicionário de campos

| Campo | Tipo   | Significado          |
|-------|--------|-----------------------|
| id    | inteiro| Identificador do registro |
| name  | texto  | Nome                  |
| note  | texto  | Observação            |
