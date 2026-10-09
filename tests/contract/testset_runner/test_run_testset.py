"""Contract tests for User Story 1 Acceptance Scenarios (quickstart.md Scenarios 1-4)
and User Story 3 (differing target configuration), per contracts/running.md.
"""

import json
from pathlib import Path

from data_access.text_matching import TextMatchingConfig
from qa_agent.models import FailureDetail, QuestionAnsweringResult
from testset_runner.comparator import compare_runs
from testset_runner.models import TargetConfiguration
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileRunStore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BUNDLED_TESTSET = REPO_ROOT / "data" / "testsets" / "orcamentos-aeb-csv.json"
MINI_TESTSET = REPO_ROOT / "tests" / "fixtures" / "testset_runner" / "mini-testset.json"
DATASET_KEY = "orcamentos-aeb-csv"
UNKNOWN_DATASET_KEY = "<none>"


class ScriptedAnswerer:
    """Returns the testset's own `expected` value verbatim as the answer, so numeric
    questions auto-grade "matched" and non-numeric ones become "needs_review" — except
    for `n`s listed in `fail_ns`, which come back `errored=True`."""

    def __init__(self, testset_path: Path, *, fail_ns: frozenset[int] = frozenset()) -> None:
        records = json.loads(testset_path.read_bytes())
        self._by_question_text = {record["question"]: record for record in records}
        self._fail_ns = fail_ns

    def answer(self, question: str) -> QuestionAnsweringResult:
        record = self._by_question_text[question]
        if record["n"] in self._fail_ns:
            return QuestionAnsweringResult(
                answer="Não foi possível processar a pergunta no momento.",
                dataset_key=DATASET_KEY,
                outcome="none",
                steps=[],
                errored=True,
            )
        return QuestionAnsweringResult(
            answer=f"A resposta é {record['expected']}.",
            dataset_key=DATASET_KEY,
            outcome="full",
            steps=[],
            errored=False,
        )


def _target(model_name: str = "fake", base_url: str | None = None) -> TargetConfiguration:
    return TargetConfiguration(model_name=model_name, base_url=base_url)


def test_full_run_produces_one_report_covering_every_question(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    assert len(run.results) == 50
    assert run.summary.total_questions == 50
    assert (tmp_path / f"{run.run_id}.json").exists()


def test_each_question_result_carries_full_per_question_detail(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    result = run.results[0]
    assert result.question
    assert result.expected
    assert result.actual_answer
    assert result.agent_outcome in ("full", "partial", "none")
    assert result.dataset_key == DATASET_KEY
    assert isinstance(result.steps, list)
    assert result.match_status in ("matched", "not_matched", "needs_review", "errored")


def test_numeric_expected_values_are_auto_graded(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    numeric_result = next(r for r in run.results if r.n == 1)
    assert numeric_result.match_status == "matched"

    tolerant_result = next(r for r in run.results if r.n == 30)
    assert tolerant_result.expected.startswith("~")
    assert tolerant_result.match_status == "matched"


def test_non_numeric_expected_values_are_always_needs_review(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    composite_result = next(r for r in run.results if r.n == 45)
    assert "/" in composite_result.expected
    assert composite_result.match_status == "needs_review"

    # n=47: a descriptive `expected` with no `expected_outcome` (n=48-50 carry one since
    # 008 and are graded on the outcome instead).
    descriptive_result = next(r for r in run.results if r.n == 47)
    assert descriptive_result.match_status == "needs_review"


def test_a_single_questions_failure_does_not_abort_the_run(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset({7})),
        store=JsonFileRunStore(tmp_path),
    )

    assert len(run.results) == 50
    assert next(r for r in run.results if r.n == 7).match_status == "errored"
    assert all(r.match_status != "errored" for r in run.results if r.n != 7)


def test_target_unreachable_when_every_eligible_question_errors(tmp_path: Path) -> None:
    all_n = {record["n"] for record in json.loads(BUNDLED_TESTSET.read_bytes())}
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset(all_n)),
        store=JsonFileRunStore(tmp_path),
    )
    assert run.summary.target_unreachable is True

    partial_run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset({7})),
        store=JsonFileRunStore(tmp_path),
    )
    assert partial_run.summary.target_unreachable is False


def test_two_runs_differing_only_in_target_both_complete_and_record_their_target(
    tmp_path: Path,
) -> None:
    run_a = run_testset(
        BUNDLED_TESTSET,
        _target(model_name="model-a"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )
    run_b = run_testset(
        BUNDLED_TESTSET,
        _target(model_name="model-b", base_url="http://localhost:8000/v1"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    assert run_a.target.model_name == "model-a"
    assert run_a.target.base_url is None
    assert run_b.target.model_name == "model-b"
    assert run_b.target.base_url == "http://localhost:8000/v1"


# --- 006 US1: failure details and per-type counts -----------------------------------

CONNECT_FAILURE = FailureDetail(
    type="ConnectError", message="[Errno 111] Connection refused", transient=False
)
AUTH_FAILURE = FailureDetail(
    type="AuthenticationError", message="Error code: 401", transient=False
)


class FailureScriptedAnswerer:
    """Answers the mini testset with the `expected` value, except `n`s mapped in
    `failures`: those come back errored carrying that `FailureDetail` (or none at all,
    as a legacy fake would)."""

    def __init__(self, failures: dict[int, FailureDetail | None]) -> None:
        records = json.loads(MINI_TESTSET.read_bytes())
        self._by_question_text = {record["question"]: record for record in records}
        self._failures = failures

    def answer(self, question: str) -> QuestionAnsweringResult:
        record = self._by_question_text[question]
        if record["n"] in self._failures:
            return QuestionAnsweringResult(
                answer="Não foi possível processar a pergunta no momento.",
                dataset_key=DATASET_KEY,
                outcome="none",
                errored=True,
                failure=self._failures[record["n"]],
            )
        return QuestionAnsweringResult(
            answer=f"A resposta é {record['expected']}.",
            dataset_key=DATASET_KEY,
            outcome="full",
        )


def test_errored_results_carry_the_answerers_failure_and_others_carry_none(
    tmp_path: Path,
) -> None:
    failures: dict[int, FailureDetail | None] = {1: CONNECT_FAILURE, 2: AUTH_FAILURE}
    run = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=FailureScriptedAnswerer(failures),
        store=JsonFileRunStore(tmp_path),
    )

    for result in run.results:
        if result.n in failures:
            assert result.match_status == "errored"
            assert result.failure == failures[result.n]
        else:
            assert result.failure is None


def test_summary_counts_errored_questions_per_failure_type(tmp_path: Path) -> None:
    run = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=FailureScriptedAnswerer({1: CONNECT_FAILURE, 4: CONNECT_FAILURE, 2: AUTH_FAILURE}),
        store=JsonFileRunStore(tmp_path),
    )

    assert run.summary.errored_by_failure_type == {"ConnectError": 2, "AuthenticationError": 1}
    assert run.summary.by_category["single-lookup"].errored_by_failure_type == {"ConnectError": 2}
    assert run.summary.by_category["calculation"].errored_by_failure_type == {
        "AuthenticationError": 1
    }
    assert run.summary.by_category["edge-cases"].errored_by_failure_type == {}


def test_errored_result_without_a_failure_is_counted_as_unknown(tmp_path: Path) -> None:
    run = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=FailureScriptedAnswerer({3: None}),
        store=JsonFileRunStore(tmp_path),
    )

    assert run.summary.errored_by_failure_type == {"unknown": 1}


def test_no_errored_questions_means_an_empty_failure_type_count(tmp_path: Path) -> None:
    run = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=FailureScriptedAnswerer({}),
        store=JsonFileRunStore(tmp_path),
    )

    assert run.summary.errored_by_failure_type == {}


# --- 008 US3: grading against expected_outcome ----------------------------------------

NOT_COVERED_RECORD = {
    "n": 1,
    "type": "edge-cases",
    "question": "Quanto foi pago ao satélite Amazônia-1 em 2020?",
    "expected": "Data not available (outside the dataset period)",
    "source": "dados_gerais/tb_geral.csv",
}


def _write_testset(tmp_path: Path, records: list[dict]) -> Path:
    path = tmp_path / "testset.json"
    path.write_text(json.dumps(records, ensure_ascii=False))
    return path


class FixedAnswerer:
    """Returns the same scripted `QuestionAnsweringResult` for every question."""

    def __init__(self, result: QuestionAnsweringResult) -> None:
        self._result = result

    def answer(self, question: str) -> QuestionAnsweringResult:
        return self._result


def _fixed(outcome, *, answer: str = "Não há dados para 2020 sobre o Amazônia-1.", errored=False, fingerprint=None):
    return FixedAnswerer(
        QuestionAnsweringResult(
            answer=answer,
            dataset_key=DATASET_KEY,
            outcome=outcome,
            errored=errored,
            briefing_fingerprint=fingerprint,
        )
    )


def test_008_us3_expected_outcome_drives_grading(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, [{**NOT_COVERED_RECORD, "expected_outcome": "none"}])
    store = JsonFileRunStore(tmp_path / "runs")

    run = run_testset(testset, _target(), answerer=_fixed("none"), store=store)
    assert run.results[0].match_status == "matched"
    assert run.results[0].expected_outcome == "none"

    run = run_testset(testset, _target(), answerer=_fixed("partial"), store=store)
    assert run.results[0].match_status == "not_matched"


def test_008_us3_6_errored_stays_errored(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, [{**NOT_COVERED_RECORD, "expected_outcome": "none"}])

    run = run_testset(
        testset,
        _target(),
        answerer=_fixed("none", answer="Não foi possível processar a pergunta.", errored=True),
        store=JsonFileRunStore(tmp_path / "runs"),
    )

    assert run.results[0].match_status == "errored"


def test_008_expected_outcome_recorded_as_none_when_absent(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, [NOT_COVERED_RECORD])

    run = run_testset(
        testset, _target(), answerer=_fixed("none"), store=JsonFileRunStore(tmp_path / "runs")
    )

    assert run.results[0].expected_outcome is None
    assert run.results[0].match_status == "needs_review"


# --- 008 US4: prompt version and briefing fingerprints on the run -----------------------


class SequenceAnswerer:
    """Returns the scripted results in order, one per question."""

    def __init__(self, results: list[QuestionAnsweringResult]) -> None:
        self._results = iter(results)

    def answer(self, question: str) -> QuestionAnsweringResult:
        return next(self._results)


def _records(count: int) -> list[dict]:
    return [{**NOT_COVERED_RECORD, "n": n, "question": f"Pergunta {n}?"} for n in range(1, count + 1)]


def _with_fingerprints(fingerprints: list[str | None], *, errored: bool = False) -> SequenceAnswerer:
    return SequenceAnswerer(
        [
            QuestionAnsweringResult(
                answer="Não há dados.",
                dataset_key=DATASET_KEY if fp else UNKNOWN_DATASET_KEY,
                outcome="none",
                errored=errored,
                briefing_fingerprint=fp,
            )
            for fp in fingerprints
        ]
    )


def test_008_us4_6_run_records_sorted_distinct_fingerprints(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, _records(4))

    run = run_testset(
        testset,
        _target(),
        answerer=_with_fingerprints(["b", "a", "b", None]),
        store=JsonFileRunStore(tmp_path / "runs"),
    )

    assert run.briefing_fingerprints == ["a", "b"]


def test_008_us4_6_same_briefing_same_fingerprint(tmp_path: Path) -> None:
    from qa_agent.prompt_loader import fingerprint

    testset = _write_testset(tmp_path, _records(2))
    store = JsonFileRunStore(tmp_path / "runs")
    same = fingerprint("Briefing A")

    run_1 = run_testset(testset, _target(), answerer=_with_fingerprints([same, same]), store=store)
    run_2 = run_testset(testset, _target(), answerer=_with_fingerprints([same, same]), store=store)
    changed = fingerprint("Briefing A, editado")
    run_3 = run_testset(testset, _target(), answerer=_with_fingerprints([changed, changed]), store=store)

    assert run_1.briefing_fingerprints == run_2.briefing_fingerprints == [same]
    assert run_3.briefing_fingerprints != run_1.briefing_fingerprints


def test_008_all_selection_failures_give_empty_list(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, _records(2))

    run = run_testset(
        testset,
        _target(),
        answerer=_with_fingerprints([None, None], errored=True),
        store=JsonFileRunStore(tmp_path / "runs"),
    )

    assert run.briefing_fingerprints == []


def test_008_us4_2_target_prompt_version_persisted(tmp_path: Path) -> None:
    testset = _write_testset(tmp_path, _records(1))
    store = JsonFileRunStore(tmp_path / "runs")

    run = run_testset(
        testset,
        TargetConfiguration(model_name="fake", prompt_version="v1"),
        answerer=_fixed("none"),
        store=store,
    )

    reloaded = store.load(tmp_path / "runs" / f"{run.run_id}.json")
    assert reloaded.target.prompt_version == "v1"


# --- 009: text matching configuration recorded on the run (FR-016) -----------------------


def test_009_text_matching_is_recorded_and_round_trips(tmp_path: Path) -> None:
    config = TextMatchingConfig(value_list_threshold=12, max_suggestions=3)
    store = JsonFileRunStore(tmp_path)
    run = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(MINI_TESTSET),
        store=store,
        text_matching=config,
    )

    assert run.text_matching == config
    assert store.load(tmp_path / f"{run.run_id}.json").text_matching == config


def test_009_text_matching_not_given_is_recorded_as_none(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run = run_testset(
        MINI_TESTSET, _target(), answerer=ScriptedAnswerer(MINI_TESTSET), store=store
    )

    assert run.text_matching is None
    assert store.load(tmp_path / f"{run.run_id}.json").text_matching is None


def test_009_compare_accepts_runs_differing_only_in_text_matching(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run_a = run_testset(
        MINI_TESTSET, _target(), answerer=ScriptedAnswerer(MINI_TESTSET), store=store
    )
    run_b = run_testset(
        MINI_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(MINI_TESTSET),
        store=store,
        text_matching=TextMatchingConfig(),
    )

    comparison = compare_runs(
        tmp_path / f"{run_a.run_id}.json", tmp_path / f"{run_b.run_id}.json", store=store
    )

    assert len(comparison.entries) == len(run_a.results)
