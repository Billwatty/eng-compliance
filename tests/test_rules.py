"""The rules engine must reproduce the worked examples exactly."""
import pytest

from app.rules import FAIL, MARGINAL, PASS, Rule, TestResult, evaluate_rule, overall, required_tests, validate_params

DENSITY = Rule("BASE-DENSITY-01", 1, "4.2", "field_density_pct_mdd", "min_and_mean",
               {"min": 97, "mean_min": 98}, "% MDD", frequency_qty=350, marginal_band=0.5)
WORKED = [98.4, 97.6, 99.1, 96.8, 98.0, 97.9, 98.6, 97.2]


def tr(vals, param="field_density_pct_mdd"):
    return [TestResult(i + 1, param, v, chainage=12030 + i * 60) for i, v in enumerate(vals)]


def by_kind(findings, kind):
    return [f for f in findings if f.kind == kind]


def test_worked_example_three_failures():
    fs = evaluate_rule(DENSITY, tr(WORKED), lot_size=3500)
    singles = by_kind(fs, "single")
    failed = [f for f in singles if f.result == FAIL]
    assert len(failed) == 1
    assert failed[0].measured == 96.8 and failed[0].deviation == -0.2 and failed[0].chainage == 12210
    mean = by_kind(fs, "mean")[0]
    assert mean.result == FAIL and mean.measured == 97.95 and mean.deviation == -0.05
    freq = by_kind(fs, "frequency")[0]
    assert freq.result == FAIL and freq.measured == 8 and freq.limit == 10 and freq.deviation == -2
    assert overall(fs) == FAIL


def test_required_tests_rounds_up():
    assert required_tests(3500, 350) == 10
    assert required_tests(3501, 350) == 11
    assert required_tests(100, 350) == 1


def test_marginal_and_near_limit_run():
    fs = evaluate_rule(DENSITY, tr([97.1, 97.2, 97.3] + [99.0] * 7), lot_size=3500)
    assert by_kind(fs, "near_limit")[0].result == MARGINAL
    assert overall(fs) == MARGINAL


def test_tolerance():
    r = Rule("LEVEL", 1, "4.2", "level_deviation_mm", "tolerance", {"design": 0, "plus": 0, "minus": 25}, "mm")
    fs = evaluate_rule(r, tr([-22, -26, 3], "level_deviation_mm"), 0)
    assert [f.result for f in fs] == [PASS, FAIL, FAIL]
    assert fs[1].deviation == -26


def test_envelope_names_the_failing_sieve():
    r = Rule("GRAD", 1, "4.2", "grading", "envelope", {"sieves": {"20": [60, 85], "0.075": [5, 15]}})
    tests = [TestResult(1, "grading:20", 70, group_ref="G1"), TestResult(2, "grading:0.075", 17.5, group_ref="G1")]
    fs = evaluate_rule(r, tests, 0)
    bad = [f for f in fs if f.result == FAIL]
    assert len(bad) == 1 and bad[0].parameter == "grading:0.075" and bad[0].deviation == 2.5


def test_concrete_cubes():
    r = Rule("CUBE", 1, "8.3", "cube_strength_mpa", "concrete_cube",
             {"fck_cube": 37, "mean_margin": 4, "individual_margin": 4, "group_size": 3}, "MPa", frequency_qty=50)
    def sets(vals):
        out, i = [], 0
        for g, vs in vals:
            for v in vs:
                i += 1
                out.append(TestResult(i, "cube_strength_mpa", v, group_ref=g, tested_on="2026-10-26"))
        return out
    ok = evaluate_rule(r, sets([("C1", (42, 43, 41)), ("C2", (44, 42, 43)), ("C3", (40, 41, 42))]), 120)
    assert overall(ok) == PASS
    low = evaluate_rule(r, sets([("C1", (38, 39, 40)), ("C2", (40, 39, 41)), ("C3", (32, 31, 33))]), 120)
    kinds = {(f.kind, f.result) for f in low}
    assert ("concrete_individual", FAIL) in kinds and ("concrete_mean", FAIL) in kinds


def test_no_results_is_a_failure():
    assert evaluate_rule(DENSITY, [], 3500)[0].kind == "no_tests"


def test_bad_params_rejected():
    with pytest.raises(ValueError):
        validate_params("min_and_mean", {"min": 97})
    with pytest.raises(ValueError):
        validate_params("envelope", {"sieves": {"20": [85, 60]}})
