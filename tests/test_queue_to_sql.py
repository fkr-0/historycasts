from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "queue_to_sql.py"
_SPEC = importlib.util.spec_from_file_location("queue_to_sql", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"failed to load module spec from {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
compile_queue_to_sql = _MODULE.compile_queue_to_sql


def test_compile_queue_to_sql_generates_transactional_script() -> None:
    queue = [
        {
            "op_id": "op-1",
            "entity_type": "episode",
            "entity_id": 42,
            "op_type": "update",
            "payload": {"fields": {"title": "Updated title", "kind": "regular"}},
            "preconditions": {"title": "Old title"},
        },
        {
            "op_id": "op-2",
            "entity_type": "relation",
            "op_type": "link",
            "payload": {"left_id": 42, "right_id": 7, "left_col": "episode_id", "right_col": "cluster_id"},
        },
        {
            "op_id": "op-3",
            "entity_type": "entity",
            "entity_id": 9,
            "op_type": "delete",
            "payload": {},
        },
    ]

    sql = compile_queue_to_sql(queue)

    assert sql.startswith("BEGIN;")
    assert "-- op op-1 (update)" in sql
    assert "UPDATE episodes SET title='Updated title', kind='regular' WHERE id=42;" in sql
    assert "INSERT OR IGNORE INTO episode_clusters (episode_id, cluster_id) VALUES (42, 7);" in sql
    assert "DELETE FROM entities WHERE id=9;" in sql
    assert sql.strip().endswith("COMMIT;")
