"""Deterministic rules engine.

Every pass or fail comes from here. AI never decides a result: it only drafts
rule cards (which an engineer approves) and reads documents (which a person
confirms). Same rule + same results => same findings, every time.

Deviation convention: measured minus limit. For a minimum, a negative
deviation fails. For a maximum, a positive deviation fails.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any, Iterable

LIMIT_TYPES = ("min", "max", "range", "min_and_mean", "tolerance", "envelope", "concrete_cube")

PASS, MARGINAL, FAIL = "pass", "marginal", "fail"
_RANK = {PASS: 0, MARGINAL: 1, FAIL: 2}


@dataclass
class Rule:
    rule_code: str
    version: int
    boq_code: str
    parameter: str
    limit_type: str
    params: dict[str, Any]
    unit: str = ""
    frequency_qty: float | None = None
    marginal_band: float = 0.0
    source_ref: str = ""

    @classmethod
    def from_row(cls, r: dict) -> "Rule":
        return cls(
            rule_code=r["rule_code"], version=r["version"], boq_code=r["boq_code"],
            parameter=r["parameter"], limit_type=r["limit_type"],
            params=json.loads(r["params_json"]) if isinstance(r["params_json"], str) else r["params_json"],
            unit=r.get("unit") or "", frequency_qty=r.get("frequency_qty"),
            marginal_band=r.get("marginal_band") or 0.0, source_ref=r.get("source_ref") or "",
        )


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class
    id: int | None
    parameter: str
    value: float
    chainage: float | None = None
    group_ref: str | None = None
    tested_on: str = ""


@dataclass
class Finding:
    rule_code: str
    version: int
    kind: str
    result: str
    parameter: str
    message: str
    measured: float | None = None
    limit: float | None = None
    deviation: float | None = None
    unit: str = ""
    test_ids: list[int] = field(default_factory=list)
    chainage: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_params(limit_type: str, params: dict[str, Any]) -> None:
    """Raise ValueError if a rule card's parameters are incomplete."""
    need = {
        "min": ["min"], "max": ["max"], "range": ["min", "max"],
        "min_and_mean": ["min", "mean_min"], "tolerance": ["design", "plus", "minus"],
        "envelope": ["sieves"], "concrete_cube": ["fck_cube", "mean_margin", "individual_margin"],
    }
    if limit_type not in need:
        raise ValueError(f"unknown limit type '{limit_type}'")
    missing = [k for k in need[limit_type] if params.get(k) is None]
    if missing:
        raise ValueError(f"{limit_type} rule needs: {', '.join(missing)}")
    if limit_type == "envelope":
        for sieve, band in params["sieves"].items():
            if not (isinstance(band, (list, tuple)) and len(band) == 2 and band[0] <= band[1]):
                raise ValueError(f"envelope band for sieve {sieve} must be [low, high]")


def _r(x: float | None) -> float | None:
    return None if x is None else round(x, 3)


def required_tests(lot_size: float, frequency_qty: float) -> int:
    return max(1, math.ceil(lot_size / frequency_qty - 1e-9))


def _frequency(rule: Rule, n_done: int, lot_size: float, ids: list[int], what: str = "tests") -> Finding | None:
    if not rule.frequency_qty:
        return None
    need = required_tests(lot_size, rule.frequency_qty)
    deficit = need - n_done
    if deficit > 0:
        return Finding(rule.rule_code, rule.version, "frequency", FAIL, rule.parameter,
                       f"{n_done} {what} done, {need} required (1 per {rule.frequency_qty:g}); {deficit} missing",
                       measured=n_done, limit=need, deviation=-deficit, test_ids=ids)
    return Finding(rule.rule_code, rule.version, "frequency", PASS, rule.parameter,
                   f"{n_done} {what} done, {need} required", measured=n_done, limit=need, deviation=n_done - need,
                   test_ids=ids)


def _near_limit_run(rule: Rule, tests: list[TestResult], lower: float, run: int = 3) -> Finding | None:
    """Flag a run of passing results that all sit just above the limit."""
    band = rule.marginal_band
    if band <= 0:
        return None
    streak: list[TestResult] = []
    for t in tests:
        if lower <= t.value < lower + band:
            streak.append(t)
            if len(streak) >= run:
                return Finding(rule.rule_code, rule.version, "near_limit", MARGINAL, rule.parameter,
                               f"{len(streak)} consecutive results within {band:g} of the limit; ask for a witnessed retest",
                               test_ids=[s.id for s in streak if s.id is not None])
        else:
            streak = []
    return None


def _single(rule: Rule, t: TestResult, lo: float | None, hi: float | None) -> Finding:
    v = t.value
    if lo is not None and v < lo:
        return Finding(rule.rule_code, rule.version, "single", FAIL, rule.parameter,
                       f"{v:g} is below the minimum {lo:g}", v, lo, _r(v - lo), rule.unit, [t.id] if t.id else [], t.chainage)
    if hi is not None and v > hi:
        return Finding(rule.rule_code, rule.version, "single", FAIL, rule.parameter,
                       f"{v:g} is above the maximum {hi:g}", v, hi, _r(v - hi), rule.unit, [t.id] if t.id else [], t.chainage)
    band = rule.marginal_band
    if band > 0 and ((lo is not None and v < lo + band) or (hi is not None and v > hi - band)):
        ref = lo if (lo is not None and v < lo + band) else hi
        return Finding(rule.rule_code, rule.version, "single", MARGINAL, rule.parameter,
                       f"{v:g} passes but is within {band:g} of the limit {ref:g}", v, ref, _r(v - ref), rule.unit,
                       [t.id] if t.id else [], t.chainage)
    ref = lo if lo is not None else hi
    return Finding(rule.rule_code, rule.version, "single", PASS, rule.parameter, f"{v:g} within limit",
                   v, ref, _r(v - ref) if ref is not None else None, rule.unit, [t.id] if t.id else [], t.chainage)


def evaluate_rule(rule: Rule, tests: Iterable[TestResult], lot_size: float) -> list[Finding]:
    tests = list(tests)
    p = rule.params
    out: list[Finding] = []

    if rule.limit_type == "envelope":
        rel = [t for t in tests if t.parameter.startswith(rule.parameter + ":")]
    else:
        rel = [t for t in tests if t.parameter == rule.parameter]
    ids = [t.id for t in rel if t.id is not None]

    if not rel:
        return [Finding(rule.rule_code, rule.version, "no_tests", FAIL, rule.parameter,
                        f"No results recorded for {rule.parameter}")]

    lt = rule.limit_type
    if lt in ("min", "max", "range", "min_and_mean"):
        lo = p.get("min") if lt in ("min", "range", "min_and_mean") else None
        hi = p.get("max") if lt in ("max", "range") else None
        out.extend(_single(rule, t, lo, hi) for t in rel)
        if lt == "min_and_mean":
            m = mean(t.value for t in rel)
            res = FAIL if m < p["mean_min"] else PASS
            out.append(Finding(rule.rule_code, rule.version, "mean", res, rule.parameter,
                               f"lot mean {m:.2f} {'is below' if res == FAIL else 'meets'} the average limit {p['mean_min']:g}",
                               _r(m), p["mean_min"], _r(m - p["mean_min"]), rule.unit, ids))
        if lo is not None:
            nl = _near_limit_run(rule, rel, lo)
            if nl:
                out.append(nl)
        f = _frequency(rule, len(rel), lot_size, ids)
        if f:
            out.append(f)

    elif lt == "tolerance":
        design, plus, minus = p["design"], p["plus"], p["minus"]
        for t in rel:
            dev = t.value - design
            bad = dev < -minus or dev > plus
            out.append(Finding(rule.rule_code, rule.version, "tolerance", FAIL if bad else PASS, rule.parameter,
                               f"{t.value:g} vs design {design:g}: {dev:+g} (allowed +{plus:g} / -{minus:g})",
                               t.value, design, _r(dev), rule.unit, [t.id] if t.id else [], t.chainage))
        f = _frequency(rule, len(rel), lot_size, ids)
        if f:
            out.append(f)

    elif lt == "envelope":
        sieves: dict[str, list[float]] = p["sieves"]
        by_sieve: dict[str, list[TestResult]] = {}
        for t in rel:
            by_sieve.setdefault(t.parameter.split(":", 1)[1], []).append(t)
        for sieve, (lo, hi) in sieves.items():
            for t in by_sieve.get(sieve, []):
                if t.value < lo or t.value > hi:
                    ref = lo if t.value < lo else hi
                    out.append(Finding(rule.rule_code, rule.version, "envelope", FAIL, f"{rule.parameter}:{sieve}",
                                       f"sieve {sieve}: {t.value:g}% passing is outside {lo:g}-{hi:g}%",
                                       t.value, ref, _r(t.value - ref), "%", [t.id] if t.id else [], t.chainage))
                else:
                    out.append(Finding(rule.rule_code, rule.version, "envelope", PASS, f"{rule.parameter}:{sieve}",
                                       f"sieve {sieve}: {t.value:g}% inside {lo:g}-{hi:g}%", t.value, None, None, "%",
                                       [t.id] if t.id else [], t.chainage))
            if sieve not in by_sieve:
                out.append(Finding(rule.rule_code, rule.version, "envelope", FAIL, f"{rule.parameter}:{sieve}",
                                   f"no result for sieve {sieve}"))
        groups = {t.group_ref or f"t{t.id}" for t in rel}
        f = _frequency(rule, len(groups), lot_size, ids, "gradings")
        if f:
            out.append(f)

    elif lt == "concrete_cube":
        # Test result = mean of the cubes in one set (group_ref). Criteria follow the
        # "initial production" form of BS EN 206 conformity by default:
        # mean of n consecutive results >= fck + mean_margin, each result >= fck - individual_margin.
        fck, mm, im = p["fck_cube"], p["mean_margin"], p["individual_margin"]
        n = int(p.get("group_size", 3))
        sets: dict[str, list[TestResult]] = {}
        for t in sorted(rel, key=lambda x: (x.tested_on, x.id or 0)):
            sets.setdefault(t.group_ref or f"t{t.id}", []).append(t)
        results = [(g, mean(x.value for x in ts), [x.id for x in ts if x.id]) for g, ts in sets.items()]
        for g, val, tids in results:
            lim = fck - im
            res = FAIL if val < lim else PASS
            out.append(Finding(rule.rule_code, rule.version, "concrete_individual", res, rule.parameter,
                               f"set {g}: {val:.1f} {'below' if res == FAIL else 'meets'} individual limit {lim:g}",
                               _r(val), lim, _r(val - lim), rule.unit, tids))
        for i in range(0, len(results), n):
            chunk = results[i:i + n]
            lim = fck + mm
            if len(chunk) < n:
                out.append(Finding(rule.rule_code, rule.version, "concrete_mean", MARGINAL, rule.parameter,
                                   f"only {len(chunk)} of {n} results for the mean criterion; assess when complete",
                                   test_ids=[x for c in chunk for x in c[2]]))
                continue
            m = mean(c[1] for c in chunk)
            res = FAIL if m < lim else PASS
            out.append(Finding(rule.rule_code, rule.version, "concrete_mean", res, rule.parameter,
                               f"mean of sets {', '.join(c[0] for c in chunk)}: {m:.1f} {'below' if res == FAIL else 'meets'} {lim:g}",
                               _r(m), lim, _r(m - lim), rule.unit, [x for c in chunk for x in c[2]]))
        f = _frequency(rule, len(sets), lot_size, ids, "cube sets")
        if f:
            out.append(f)
    else:
        raise ValueError(f"unknown limit type '{lt}'")
    return out


def overall(findings: Iterable[Finding]) -> str:
    worst = PASS
    for f in findings:
        if _RANK[f.result] > _RANK[worst]:
            worst = f.result
    return worst
