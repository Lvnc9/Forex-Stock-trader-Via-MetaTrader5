"""Assemble LS → armpit → head → armpit → RS candidate sequences."""

from __future__ import annotations

from dataclasses import dataclass

from apps.strategies.patterns.head_shoulders.pivots import Pivot
from apps.strategies.patterns.head_shoulders.spec import HSSpec


@dataclass
class PatternCandidate:
    direction: str  # top | inverse
    ls: Pivot
    armpit1: Pivot
    head: Pivot
    armpit2: Pivot
    rs: Pivot
    scale: str


def _merge_key(head_index: int, merge_bars: int) -> int:
    return head_index // max(merge_bars, 1)


def _scan_top(pivots: list[Pivot], scale: str) -> list[PatternCandidate]:
    ordered = sorted(pivots, key=lambda p: p.index)
    out: list[PatternCandidate] = []
    for i in range(len(ordered) - 4):
        w = ordered[i : i + 5]
        kinds = [p.kind for p in w]
        if kinds != ["high", "low", "high", "low", "high"]:
            continue
        ls, a1, head, a2, rs = w
        if head.price <= ls.price or head.price <= rs.price:
            continue
        if not (ls.index < a1.index < head.index < a2.index < rs.index):
            continue
        out.append(PatternCandidate("top", ls, a1, head, a2, rs, scale))
    return out


def _scan_inverse(pivots: list[Pivot], scale: str) -> list[PatternCandidate]:
    ordered = sorted(pivots, key=lambda p: p.index)
    out: list[PatternCandidate] = []
    for i in range(len(ordered) - 4):
        w = ordered[i : i + 5]
        kinds = [p.kind for p in w]
        if kinds != ["low", "high", "low", "high", "low"]:
            continue
        ls, a1, head, a2, rs = w
        if head.price >= ls.price or head.price >= rs.price:
            continue
        if not (ls.index < a1.index < head.index < a2.index < rs.index):
            continue
        out.append(PatternCandidate("inverse", ls, a1, head, a2, rs, scale))
    return out


def assemble_top(short: list[Pivot], medium: list[Pivot], spec: HSSpec) -> list[PatternCandidate]:
    out: list[PatternCandidate] = []
    seen: set[tuple[str, int]] = set()
    for scale, pivots in (("short", short), ("medium", medium)):
        for cand in _scan_top(pivots, scale):
            key = (cand.direction, cand.head.index)
            if key in seen:
                continue
            seen.add(key)
            out.append(cand)
    return out


def assemble_inverse(short: list[Pivot], medium: list[Pivot], spec: HSSpec) -> list[PatternCandidate]:
    out: list[PatternCandidate] = []
    seen: set[tuple[str, int]] = set()
    for scale, pivots in (("short", short), ("medium", medium)):
        for cand in _scan_inverse(pivots, scale):
            key = (cand.direction, cand.head.index)
            if key in seen:
                continue
            seen.add(key)
            out.append(cand)
    return out


def merge_dual_scale(
    tops: list[PatternCandidate],
    inverses: list[PatternCandidate],
    spec: HSSpec,
) -> list[PatternCandidate]:
    """Prefer medium scale when head indices agree within merge window."""
    all_c = tops + inverses
    if not spec.dual_scale_required:
        return all_c

    by_head: dict[tuple[str, int], list[PatternCandidate]] = {}
    for c in all_c:
        bucket = _merge_key(c.head.index, spec.merge_head_bars)
        by_head.setdefault((c.direction, bucket), []).append(c)

    merged: list[PatternCandidate] = []
    for group in by_head.values():
        medium = [c for c in group if c.scale == "medium"]
        if medium:
            merged.append(max(medium, key=lambda c: c.head.index))
        elif group:
            merged.append(group[0])
    return merged
