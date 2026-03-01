#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TABLE_MAP = {
    "episode": "episodes",
    "span": "time_spans",
    "place": "places",
    "entity": "entities",
    "cluster": "clusters",
    "keyword": "keywords",
    "relation": "episode_clusters",
}


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).replace("'", "''")
    return f"'{s}'"


def op_to_sql(op: dict[str, Any]) -> str:
    op_type = str(op.get("op_type", "")).lower()
    entity_type = str(op.get("entity_type", "")).lower()
    entity_id = op.get("entity_id")
    payload = op.get("payload") or {}
    table = str(payload.get("table") or TABLE_MAP.get(entity_type) or entity_type)

    if op_type == "update":
        cols = payload.get("fields") or payload
        if not isinstance(cols, dict) or not cols:
            raise ValueError(f"update op {op.get('op_id')} missing payload fields")
        set_clause = ", ".join(f"{k}={_sql_literal(v)}" for k, v in cols.items() if k != "table")
        return f"UPDATE {table} SET {set_clause} WHERE id={_sql_literal(entity_id)};"

    if op_type == "delete":
        return f"DELETE FROM {table} WHERE id={_sql_literal(entity_id)};"

    if op_type == "insert":
        row = payload.get("fields") or payload
        if not isinstance(row, dict) or not row:
            raise ValueError(f"insert op {op.get('op_id')} missing payload fields")
        row = {k: v for k, v in row.items() if k != "table"}
        cols = ", ".join(row.keys())
        vals = ", ".join(_sql_literal(v) for v in row.values())
        return f"INSERT INTO {table} ({cols}) VALUES ({vals});"

    if op_type in {"link", "unlink"}:
        left = payload.get("left_id")
        right = payload.get("right_id")
        left_col = payload.get("left_col", "episode_id")
        right_col = payload.get("right_col", "cluster_id")
        if op_type == "link":
            return (
                f"INSERT OR IGNORE INTO {table} ({left_col}, {right_col}) "
                f"VALUES ({_sql_literal(left)}, {_sql_literal(right)});"
            )
        return (
            f"DELETE FROM {table} WHERE {left_col}={_sql_literal(left)} "
            f"AND {right_col}={_sql_literal(right)};"
        )

    raise ValueError(f"Unsupported op_type: {op_type}")


def compile_queue_to_sql(queue: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("BEGIN;")
    for op in queue:
        op_id = op.get("op_id", "unknown")
        preconditions = op.get("preconditions")
        if preconditions:
            lines.append(
                f"-- preconditions for {op_id}: {json.dumps(preconditions, ensure_ascii=False)}"
            )
        lines.append(f"-- op {op_id} ({op.get('op_type')})")
        lines.append(op_to_sql(op))
    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


def _load_ops(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("operations"), list):
        return payload["operations"]
    raise ValueError('Input must be an array of ops or {"operations": [...]}')


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile local operation queue JSON into SQL script")
    ap.add_argument("--in", dest="in_path", required=True, help="Input queue JSON path")
    ap.add_argument(
        "--out", dest="out_path", default="-", help="Output SQL path, or '-' for stdout"
    )
    args = ap.parse_args()

    ops = _load_ops(Path(args.in_path))
    sql = compile_queue_to_sql(ops)
    if args.out_path == "-":
        print(sql, end="")
    else:
        Path(args.out_path).write_text(sql, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
