from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RegressionCase:
    name: str
    question: str
    expected_sql_patterns: list[str] = field(default_factory=list)
    expected_metric: str | None = None
    expected_dimensions: list[str] = field(default_factory=list)
    expected_filters: dict[str, str] = field(default_factory=dict)
    expect_error: str | None = None
    must_execute: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    case: RegressionCase
    analyze_ok: bool = False
    metric_ok: bool = True
    dimension_ok: bool = True
    filter_ok: bool = True
    executed: bool = False
    execution_ok: bool = False
    sql_ok: bool = True
    latency_s: float = 0.0
    error: str | None = None
    sql_preview: str | None = None


@dataclass
class RegressionReport:
    results: list[CaseResult]
    execution_target: float = 0.95
    accuracy_target: float = 0.90
    metric_target: float = 0.95
    dimension_target: float = 0.95
    latency_target_s: float = 10.0

    @property
    def total(self) -> int:
        return len(self.results)

    def _must_execute(self) -> list[CaseResult]:
        return [r for r in self.results if r.case.must_execute and not r.case.expect_error]

    def execution_rate(self) -> float:
        items = self._must_execute()
        if not items:
            return 1.0
        return sum(1 for r in items if r.execution_ok) / len(items)

    def sql_accuracy(self) -> float:
        executed = [r for r in self.results if r.executed and r.execution_ok]
        if not executed:
            return 1.0
        return sum(1 for r in executed if r.sql_ok) / len(executed)

    def metric_resolution(self) -> float:
        items = [
            r
            for r in self.results
            if r.case.expected_metric and not r.case.expect_error
        ]
        if not items:
            return 1.0
        return sum(1 for r in items if r.metric_ok) / len(items)

    def dimension_resolution(self) -> float:
        items = [
            r
            for r in self.results
            if r.case.expected_dimensions and not r.case.expect_error
        ]
        if not items:
            return 1.0
        return sum(1 for r in items if r.dimension_ok) / len(items)

    def max_latency(self) -> float:
        return max((r.latency_s for r in self.results if r.executed), default=0.0)

    def passes_targets(self) -> bool:
        return (
            self.execution_rate() >= self.execution_target
            and self.sql_accuracy() >= self.accuracy_target
            and self.metric_resolution() >= self.metric_target
            and self.dimension_resolution() >= self.dimension_target
            and self.max_latency() <= self.latency_target_s
        )

    def format_summary(self) -> str:
        lines = [
            "--- Regression Summary ---",
            f"Cases: {self.total}",
            f"SQL execution success: {self.execution_rate():.1%} (target ≥ {self.execution_target:.0%})",
            f"SQL accuracy: {self.sql_accuracy():.1%} (target ≥ {self.accuracy_target:.0%})",
            f"Metric resolution: {self.metric_resolution():.1%} (target ≥ {self.metric_target:.0%})",
            f"Dimension resolution: {self.dimension_resolution():.1%} (target ≥ {self.dimension_target:.0%})",
            f"Max latency: {self.max_latency():.2f}s (target < {self.latency_target_s:.0f}s)",
            f"Overall: {'PASS' if self.passes_targets() else 'FAIL'}",
        ]
        failures = [r for r in self.results if _case_failed(r)]
        if failures:
            lines.append("")
            lines.append(f"Failed cases ({len(failures)}):")
            for result in failures[:15]:
                lines.append(f"  - {result.case.name}: {result.error or 'check mismatch'}")
            if len(failures) > 15:
                lines.append(f"  ... and {len(failures) - 15} more")
        return "\n".join(lines)


def _case_failed(result: CaseResult) -> bool:
    case = result.case
    if case.expect_error:
        return result.error != case.expect_error
    if case.must_execute and not result.execution_ok:
        return True
    if result.executed and not result.sql_ok:
        return True
    if case.expected_metric and not result.metric_ok:
        return True
    if case.expected_dimensions and not result.dimension_ok:
        return True
    if case.expected_filters and not result.filter_ok:
        return True
    return False


def load_cases(cases_dir: Path) -> list[RegressionCase]:
    cases: list[RegressionCase] = []
    for path in sorted(cases_dir.glob("*.json")):
        payload = json.loads(path.read_text())
        for item in payload:
            cases.append(RegressionCase(**item))
    return cases


def _http_json(url: str, method: str = "GET", body: dict | None = None) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return e.code, payload


def _analyze(api_url: str, question: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    query = urllib.parse.urlencode({"question": question})
    status, payload = _http_json(f"{api_url}/analyze?{query}")
    if status == 200:
        return True, payload, None
    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        return False, None, detail.get("error")
    return False, None, str(detail)


def _ask(api_url: str, question: str) -> tuple[bool, dict[str, Any] | None, str | None, float]:
    start = time.perf_counter()
    status, payload = _http_json(
        f"{api_url}/ask",
        method="POST",
        body={"question": question},
    )
    elapsed = time.perf_counter() - start
    if status == 200:
        return True, payload, None, elapsed
    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        return False, None, detail.get("error"), elapsed
    return False, None, str(detail), elapsed


def run_regression(api_url: str, cases_dir: Path) -> RegressionReport:
    cases = load_cases(cases_dir)
    results: list[CaseResult] = []

    for case in cases:
        result = CaseResult(case=case)

        if case.expect_error:
            _, _, ask_error, latency = _ask(api_url, case.question)
            result.latency_s = latency
            result.error = ask_error
            result.execution_ok = ask_error == case.expect_error
            results.append(result)
            continue

        analyze_success, intent, analyze_error = _analyze(api_url, case.question)
        result.analyze_ok = analyze_success
        if not analyze_success:
            result.error = analyze_error or "analyze failed"
            result.metric_ok = False
            result.dimension_ok = False
            results.append(result)
            continue

        assert intent is not None
        if case.expected_metric:
            result.metric_ok = intent.get("metric") == case.expected_metric
        if case.expected_dimensions:
            result.dimension_ok = sorted(intent.get("dimensions", [])) == sorted(
                case.expected_dimensions
            )
        if case.expected_filters:
            result.filter_ok = all(
                intent.get("filters", {}).get(key) == value
                for key, value in case.expected_filters.items()
            )

        if case.must_execute:
            ask_success, payload, ask_error, latency = _ask(api_url, case.question)
            result.executed = True
            result.latency_s = latency
            result.execution_ok = ask_success
            if not ask_success:
                result.error = ask_error or "ask failed"
                results.append(result)
                continue

            assert payload is not None
            sql = payload.get("sql", "")
            result.sql_preview = sql[:120]
            if case.expected_sql_patterns:
                sql_lower = sql.lower()
                result.sql_ok = all(
                    pattern.lower() in sql_lower for pattern in case.expected_sql_patterns
                )

        results.append(result)

    return RegressionReport(results=results)
