"""Utility helpers for product normalization.

Kept intentionally small and dependency-free so it can be imported
from models/migrations safely.
"""

import re
from typing import Optional

NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    normalized = name.lower()
    normalized = normalized.replace("&", " and ")
    normalized = NORMALIZE_RE.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or None
