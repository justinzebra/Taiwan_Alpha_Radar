"""Portable column types.

``JSONB`` is the right choice on PostgreSQL (the production target), but the
generic ``JSON`` variant lets the exact same models run on SQLite for fast,
DB-backed integration tests. ``with_variant`` keeps JSONB on Postgres and only
swaps in JSON when the dialect is sqlite.
"""
from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Use JSONB on Postgres, JSON elsewhere (e.g. sqlite test runs).
JSONType = JSONB().with_variant(JSON(), "sqlite")
