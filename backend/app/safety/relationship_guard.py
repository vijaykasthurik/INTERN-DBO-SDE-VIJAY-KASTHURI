"""Verified base-table joins shared by planning and read-only SQL execution."""
from typing import Any

import duckdb
import sqlglot
from sqlglot import exp

from app.data.relationships import RelationshipDetector
from app.safety.sql_validator import SQLSecurityError


def reliable_relationships(db_path: str, tables: list[str]) -> list[dict[str, Any]]:
    candidates = RelationshipDetector().detect_table_relationships(db_path,tables)
    output: list[dict[str, Any]] = []
    con = duckdb.connect(db_path,read_only=True)
    try:
        for edge in candidates:
            if edge["confidence"] < 0.95:
                continue
            for fact,fk,dim,dk in [(edge["from_table"],edge["from_column"],edge["to_table"],edge["to_column"]),(edge["to_table"],edge["to_column"],edge["from_table"],edge["from_column"])]:
                unique = con.execute(f'SELECT COUNT(*) = COUNT(DISTINCT "{dk}") FROM "{dim}"').fetchone()
                if not unique or not unique[0]:
                    continue
                source = con.execute(f'SELECT COUNT(*) FROM "{fact}"').fetchone()
                assert source is not None
                joined = con.execute(f'SELECT COUNT(*),COUNT(d."{dk}") FROM "{fact}" f LEFT JOIN "{dim}" d ON f."{fk}"=d."{dk}"').fetchone()
                if joined and joined[0] == source[0] and joined[1] >= source[0]*0.95:
                    output.append({"from_table":fact,"from_column":fk,"to_table":dim,"to_column":dk,"source_rows":source[0],"joined_rows":joined[0],"fanout_check":"passed"})
    finally:
        con.close()
    return output


def validate_base_joins(sql: str, db_path: str, tables: list[str]) -> list[dict[str, Any]]:
    tree = sqlglot.parse_one(sql,read="duckdb")
    joins = list(tree.find_all(exp.Join))
    if not joins:
        return []
    edges = reliable_relationships(db_path,tables)
    aliases = {table.alias_or_name:table.name for table in tree.find_all(exp.Table) if table.name in tables}
    used = []
    for join in joins:
        if not isinstance(join.this,exp.Table) or join.this.name not in tables:
            continue
        pairs = []
        condition = join.args.get("on")
        if condition is not None:
            for equality in condition.find_all(exp.EQ):
                left,right = equality.left,equality.right
                if isinstance(left,exp.Column) and isinstance(right,exp.Column) and left.table in aliases and right.table in aliases:
                    pairs.append((aliases[left.table],left.name,aliases[right.table],right.name))
        for key in join.args.get("using") or []:
            for alias,table in aliases.items():
                if alias != join.this.alias_or_name:
                    pairs.append((table,key.name,join.this.name,key.name))
        matching = [edge for edge in edges if (edge["from_table"],edge["from_column"],edge["to_table"],edge["to_column"]) in pairs or (edge["to_table"],edge["to_column"],edge["from_table"],edge["from_column"]) in pairs]
        if not matching:
            raise SQLSecurityError("Join rejected: no matching relationship passed overlap, unique-key and row-count fan-out checks.")
        used.extend(matching)
    return used
