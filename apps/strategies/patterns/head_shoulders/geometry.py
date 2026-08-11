"""Geometry validation and pattern scoring."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.bars import Bar
from apps.strategies.patterns.head_shoulders.assembler import PatternCandidate
from apps.strategies.patterns.head_shoulders.atr import atr_at, compute_atr
from apps.strategies.patterns.head_shoulders.neckline import neckline_kind, neckline_price_at, neckline_slope_norm
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass
class GeometryResult:
    valid: bool
    hard_fail: str | None
    score: float
    H: float
    neckline_slope: str
    dual_scale_bonus: bool


def _prior_trend_ok(
    bars: list[Bar],
    ls_index: int,
    direction: str,
    spec: HSSpec,
    atr: list[float],
) -> tuple[bool, float]:
    start = max(0, ls_index - spec.prior_trend_bars)
    if start >= ls_index:
        return False, 0.0
    a = atr_at(atr, ls_index)
    if direction == "top":
        move = bars[ls_index].close - bars[start].close
        ok = move >= spec.min_prior_move_atr * a
    else:
        move = bars[start].close - bars[ls_index].close
        ok = move >= spec.min_prior_move_atr * a
    return ok, move / a if a > 0 else 0.0


def evaluate_geometry(
    candidate: PatternCandidate,
    bars: list[Bar],
    spec: HSSpec,
    *,
    dual_scale_hit: bool = False,
) -> GeometryResult:
    atr = compute_atr(bars, spec.atr_period)
    hi = candidate.head.index
    a = atr_at(atr, hi)

    nl_at_head = neckline_price_at(
        candidate.armpit1.index,
        candidate.armpit1.price,
        candidate.armpit2.index,
        candidate.armpit2.price,
        hi,
    )
    h_val = abs(candidate.head.price - nl_at_head)
    slope_raw = neckline_slope_norm(
        candidate.armpit1.index,
        candidate.armpit1.price,
        candidate.armpit2.index,
        candidate.armpit2.price,
        a,
    )
    nk = neckline_kind(
        candidate.armpit1.price,
        candidate.armpit2.price,
        spec.flat_eps_atr,
        a,
    )

    if slope_raw > spec.max_neckline_slope:
        return GeometryResult(False, "neckline_slope_exceeds_max", 0.0, h_val, nk, dual_scale_hit)

    prior_ok, prior_score = _prior_trend_ok(bars, candidate.ls.index, candidate.direction, spec, atr)
    if not prior_ok:
        return GeometryResult(False, "prior_trend_hard_fail", 0.0, h_val, nk, dual_scale_hit)

    if candidate.direction == "top":
        prom = candidate.head.price - max(candidate.ls.price, candidate.rs.price)
    else:
        prom = min(candidate.ls.price, candidate.rs.price) - candidate.head.price
    prom_atr = prom / a if a > 0 else 0.0
    if prom_atr < spec.head_prominence_atr:
        return GeometryResult(False, "head_prominence_hard_fail", 0.0, h_val, nk, dual_scale_hit)

    shoulder_diff = abs(candidate.ls.price - candidate.rs.price) / a if a > 0 else 999.0
    left_span = candidate.head.index - candidate.ls.index
    right_span = candidate.rs.index - candidate.head.index
    denom = max(left_span, right_span, 1)
    time_asym = abs(left_span - right_span) / denom

    w = spec.score_weights()
    score = 0.0
    score += w["prior_trend"] * min(prior_score / spec.min_prior_move_atr, 1.0)
    score += w["head_prominence"] * min(prom_atr / (spec.head_prominence_atr * 2), 1.0)
    score += w["shoulder_symmetry"] * _soft_score(shoulder_diff, spec.shoulder_tol, spec.soft_tol_mult)
    score += w["time_symmetry"] * _soft_score(time_asym, spec.time_tol, spec.soft_tol_mult)
    score += w["neckline_quality"] * (1.0 if slope_raw <= spec.max_neckline_slope * 0.75 else 0.5)
    score += w["volume"] * 0.0
    if dual_scale_hit:
        score += w["dual_scale_agreement"]

    valid = score >= spec.min_score_threshold
    return GeometryResult(valid, None, score, h_val, nk, dual_scale_hit)


def _soft_score(value: float, tol: float, soft_mult: float) -> float:
    if value <= tol:
        return 1.0
    if value <= tol * soft_mult:
        return 0.5
    return 0.0
