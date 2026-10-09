# Contract: Schema Inspection with Low-Cardinality Value Lists

Delta to 001 [contracts/inspection.md](../../001-data-access-tools/contracts/inspection.md).
Models: [data-model.md](../data-model.md) (`FieldInfo`, `SchemaInspectionResult`).
Rationale: [research.md](../research.md) R5.

```python
def inspect_schema(
    dataset: Dataset, identifier: str, *, text_matching: TextMatchingConfig = TextMatchingConfig()
) -> SchemaInspectionResult: ...
```

## Output

Everything 001 specifies is unchanged: which fields are reported (fields observed in the
sample), their order, `type`, and `sample` (≤ `SAMPLE_SIZE_CAP` raw records) (FR-017).
Added:

- `value_list_threshold`: `text_matching.value_list_threshold`.
- For each reported field, over **all** rows of the source (not the sample):
  - `distinct_count`: number of distinct non-missing raw values.
  - `values`: when `distinct_count <= value_list_threshold`, all of them as stored, sorted
    by code point. Otherwise `null`.

There is no cap on value length or total size. The threshold is the only limit (FR-014,
Clarifications Q4).

Errors: unchanged.

## Behavioral requirements (traceability)

| Scenario | Setup | Expected |
|---|---|---|
| US3-AS1 | field with 2 distinct values, only 1 in the first 20 rows | both listed |
| US3-AS2 | field with exactly `threshold` distinct values | all listed, code-point order, raw spelling |
| US3-AS3 | field with `threshold + 1` values | `values: null`, `distinct_count = threshold + 1` |
| US3-AS4 | field with empty/whitespace cells | not listed as a value, not counted |
| US3-AS5 | any source | `identifier`, `fields[].name/type`, `sample` equal to the pre-009 output |
| Edge | "Programa X" and "PROGRAMA X" | two entries |
| Edge | `threshold = 0` | every field `values: null` |
| SC-003 | `dados_gerais/tb_geral.csv` | `nome_unidade` (2), `nome_programa` (13), `data_ano` (20) fully listed; `nome_acao` (116) and monetary fields `null` |
