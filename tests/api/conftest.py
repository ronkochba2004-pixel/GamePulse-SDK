"""Shared fixtures that swap Supabase for an in-memory fake.

This lets the API layer be tested in CI without real Supabase credentials.
"""
from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import pytest

# Make sure the API can import without real env vars.
os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake")


class _Table:
    def __init__(self, store: FakeStore, name: str) -> None:
        self.store = store
        self.name = name
        self._filters: list[tuple[str, str, Any]] = []
        self._in: list[tuple[str, list[Any]]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._payload: list[dict] | dict | None = None
        self._op: str | None = None
        self._select_cols: str | None = None
        self._on_conflict: str | None = None
        self._ignore_duplicates: bool = False
        self._update: dict | None = None

    # builder methods --------------------------------------------------
    def select(self, cols: str = "*") -> _Table:
        self._op = self._op or "select"
        self._select_cols = cols
        return self

    def insert(self, payload: dict | list[dict]) -> _Table:
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict: str | None = None,
               ignore_duplicates: bool = False) -> _Table:
        self._op = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        self._ignore_duplicates = ignore_duplicates
        return self

    def update(self, values: dict) -> _Table:
        self._op = "update"
        self._update = values
        return self

    def eq(self, col: str, val: Any) -> _Table:
        self._filters.append((col, "eq", val))
        return self

    def gte(self, col: str, val: Any) -> _Table:
        self._filters.append((col, "gte", val))
        return self

    def in_(self, col: str, vals: list[Any]) -> _Table:
        self._in.append((col, list(vals)))
        return self

    def order(self, col: str, desc: bool = False) -> _Table:
        self._order = (col, desc)
        return self

    def limit(self, n: int) -> _Table:
        self._limit = n
        return self

    # execution --------------------------------------------------------
    def _matches(self, row: dict) -> bool:
        for col, op, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "gte" and not (row.get(col) is not None and row[col] >= val):
                return False
        for col, vals in self._in:
            if row.get(col) not in vals:
                return False
        return True

    def execute(self):
        rows = self.store.tables.setdefault(self.name, [])

        if self._op == "select":
            out = [r for r in rows if self._matches(r)]
            if self._order:
                col, desc = self._order
                out.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
            if self._limit is not None:
                out = out[: self._limit]
            return _Result(out)

        if self._op == "insert":
            payload = self._payload
            items = payload if isinstance(payload, list) else [payload]
            inserted = []
            for item in items:
                item = dict(item)
                item.setdefault("id", str(uuid4()))
                rows.append(item)
                inserted.append(item)
            return _Result(inserted)

        if self._op == "upsert":
            payload = self._payload
            items = payload if isinstance(payload, list) else [payload]
            inserted = []
            conflict_cols = (self._on_conflict or "").split(",") if self._on_conflict else []
            for item in items:
                item = dict(item)
                existing = None
                if conflict_cols:
                    for r in rows:
                        if all(r.get(c) == item.get(c) for c in conflict_cols):
                            existing = r
                            break
                if existing is not None:
                    if self._ignore_duplicates:
                        continue
                    existing.update(item)
                    inserted.append(existing)
                else:
                    item.setdefault("id", str(uuid4()))
                    rows.append(item)
                    inserted.append(item)
            return _Result(inserted)

        if self._op == "update":
            updated = []
            for r in rows:
                if self._matches(r):
                    r.update(self._update or {})
                    updated.append(r)
            return _Result(updated)

        return _Result([])


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _SchemaProxy:
    def __init__(self, store: FakeStore) -> None:
        self.store = store

    def table(self, name: str) -> _Table:
        return _Table(self.store, name)


class FakeStore:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.store = FakeStore()

    def schema(self, _name: str) -> _SchemaProxy:
        return _SchemaProxy(self.store)


@pytest.fixture
def fake_sb() -> FakeSupabaseClient:
    return FakeSupabaseClient()


@pytest.fixture
def client(fake_sb):
    from app.db import supabase as supa_mod
    from app.main import app
    from fastapi.testclient import TestClient

    app.dependency_overrides[supa_mod.get_supabase] = lambda: fake_sb

    # Seed a demo project with a known API key.
    import hashlib
    project_id = str(uuid4())
    fake_sb.store.tables.setdefault("projects", []).append(
        {
            "id": project_id,
            "name": "Demo",
            "slug": "demo",
            "api_key_hash": hashlib.sha256(b"demo-key").hexdigest(),
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )

    c = TestClient(app)
    c.headers.update({"X-GamePulse-Key": "demo-key"})
    try:
        yield c
    finally:
        app.dependency_overrides.clear()
