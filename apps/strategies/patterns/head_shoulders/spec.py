"""Load tunables from hs-curriculum/hs-spec.v1.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _spec_path() -> Path:
    return _repo_root() / "hs-curriculum" / "hs-spec.v1.json"


def _val(section: dict[str, Any], key: str, default: float | int | bool) -> float | int | bool:
    node = section.get(key)
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    if node is not None:
        return node
    return default


@dataclass(frozen=True)
class HSSpec:
    swing_l_short: int
    swing_l_medium: int
    min_pivot_atr: float
    merge_head_bars: int
    dual_scale_required: bool
    prior_trend_bars: int
    min_prior_move_atr: float
    head_prominence_atr: float
    shoulder_tol: float
    time_tol: float
    width_tol: float
    soft_tol_mult: float
    min_atr_mult: float
    max_neckline_slope: float
    flat_eps_atr: float
    retest_max_bars: int
    enter_next_open: bool
    sl_atr_buffer: float
    tp1_mult_h: float
    tp2_mult_h: float
    min_score_threshold: float
    score_weight_prior_trend: float
    score_weight_head_prominence: float
    score_weight_shoulder_symmetry: float
    score_weight_time_symmetry: float
    score_weight_neckline_quality: float
    score_weight_volume: float
    score_weight_dual_scale: float
    atr_period: int = 14

    def score_weights(self) -> dict[str, float]:
        return {
            "prior_trend": self.score_weight_prior_trend,
            "head_prominence": self.score_weight_head_prominence,
            "shoulder_symmetry": self.score_weight_shoulder_symmetry,
            "time_symmetry": self.score_weight_time_symmetry,
            "neckline_quality": self.score_weight_neckline_quality,
            "volume": self.score_weight_volume,
            "dual_scale_agreement": self.score_weight_dual_scale,
        }

    @classmethod
    def load(cls, path: Path | None = None) -> HSSpec:
        raw = json.loads((path or _spec_path()).read_text(encoding="utf-8"))
        piv = raw["pivots"]
        prior = raw["prior_trend"]
        geo = raw["geometry"]
        neck = raw["neckline"]
        entry = raw["entry"]
        stops = raw["stops_targets"]
        score = raw["score"]
        return cls(
            swing_l_short=int(_val(piv, "swing_L_short", 3)),
            swing_l_medium=int(_val(piv, "swing_L_medium", 8)),
            min_pivot_atr=float(_val(piv, "min_pivot_atr", 0.5)),
            merge_head_bars=int(_val(piv, "merge_head_bars", 3)),
            dual_scale_required=bool(piv.get("dual_scale_required", True)),
            prior_trend_bars=int(_val(prior, "prior_trend_bars", 50)),
            min_prior_move_atr=float(_val(prior, "min_prior_move_atr", 2.0)),
            head_prominence_atr=float(_val(geo, "head_prominence_atr", 0.5)),
            shoulder_tol=float(_val(geo, "shoulder_tol", 1.0)),
            time_tol=float(_val(geo, "time_tol", 0.35)),
            width_tol=float(_val(geo, "width_tol", 0.40)),
            soft_tol_mult=float(_val(geo, "soft_tol_mult", 1.25)),
            min_atr_mult=float(_val(geo, "min_atr_mult", 1.0)),
            max_neckline_slope=float(_val(geo, "max_neckline_slope", 0.15)),
            flat_eps_atr=float(_val(neck, "flat_eps_atr", 0.1)),
            retest_max_bars=int(_val(entry["modes"]["B"], "retest_max_bars", 15)),
            enter_next_open=bool(_val(entry["modes"]["A"], "enter_next_open", False)),
            sl_atr_buffer=float(_val(stops["SL"], "sl_atr_buffer", 0.25)),
            tp1_mult_h=float(_val(stops["TP"]["TP1"], "mult_H", 0.5)),
            tp2_mult_h=float(_val(stops["TP"]["TP2"], "mult_H", 0.51)),
            min_score_threshold=float(_val(score, "MinScoreThreshold", 60)),
            score_weight_prior_trend=float(_val(score["weights"], "prior_trend", 15)),
            score_weight_head_prominence=float(_val(score["weights"], "head_prominence", 20)),
            score_weight_shoulder_symmetry=float(_val(score["weights"], "shoulder_symmetry", 20)),
            score_weight_time_symmetry=float(_val(score["weights"], "time_symmetry", 15)),
            score_weight_neckline_quality=float(_val(score["weights"], "neckline_quality", 15)),
            score_weight_volume=float(_val(score["weights"], "volume", 10)),
            score_weight_dual_scale=float(_val(score["weights"], "dual_scale_agreement", 5)),
        )


@lru_cache(maxsize=1)
def get_spec() -> HSSpec:
    return HSSpec.load()


def spec_from_parameters(parameters: dict[str, Any]) -> HSSpec:
    base = get_spec()
    return replace(
        base,
        swing_l_short=int(parameters.get("swing_L_short", base.swing_l_short)),
        swing_l_medium=int(parameters.get("swing_L_medium", base.swing_l_medium)),
        min_score_threshold=float(parameters.get("min_score", base.min_score_threshold)),
        prior_trend_bars=int(parameters.get("prior_trend_bars", base.prior_trend_bars)),
        tp2_mult_h=float(parameters.get("tp2_k", base.tp2_mult_h)),
    )
