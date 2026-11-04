"""Relationship graph detector: infers foreign keys and join paths across user tables."""

from typing import Any

import duckdb


class RelationshipEdge:
    """Directed or undirected join candidate link between two tables."""

    def __init__(
        self,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        confidence: float,
        overlap_ratio: float,
        relationship_type: str = "many-to-one",
    ) -> None:
        self.from_table = from_table
        self.from_column = from_column
        self.to_table = to_table
        self.to_column = to_column
        self.confidence = round(confidence, 3)
        self.overlap_ratio = round(overlap_ratio, 3)
        self.relationship_type = relationship_type

    def to_dict(self) -> dict[str, Any]:
        """Convert relationship edge to dictionary."""
        return {
            "from_table": self.from_table,
            "from_column": self.from_column,
            "to_table": self.to_table,
            "to_column": self.to_column,
            "confidence": self.confidence,
            "overlap_ratio": self.overlap_ratio,
            "relationship_type": self.relationship_type,
        }


class RelationshipDetector:
    """Discovers join candidates based on column name alignment and value set intersection."""

    def detect_table_relationships(
        self,
        db_path: str,
        table_names: list[str],
    ) -> list[dict[str, Any]]:
        """Identify foreign key candidates across all pairs of tables in DuckDB."""
        if len(table_names) < 2:
            return []

        con = duckdb.connect(db_path, read_only=True)
        edges: list[RelationshipEdge] = []

        try:
            # Map table -> columns
            table_cols: dict[str, list[tuple[str, str]]] = {}
            for t in table_names:
                cols = con.execute(f'DESCRIBE "{t}";').fetchall()
                table_cols[t] = [(str(r[0]), str(r[1]).upper()) for r in cols]

            # Cross-compare pairs
            for i in range(len(table_names)):
                for j in range(i + 1, len(table_names)):
                    t1, t2 = table_names[i], table_names[j]
                    cols1, cols2 = table_cols[t1], table_cols[t2]

                    for c1, _type1 in cols1:
                        for c2, _type2 in cols2:
                            # 1. Name match / suffix match
                            name_match = False
                            c1_l, c2_l = c1.lower(), c2.lower()

                            if c1_l == c2_l or c1_l.endswith("_id") and c2_l == "id" or c2_l.endswith("_id") and c1_l == "id":
                                name_match = True

                            if not name_match:
                                continue

                            # 2. Check value set overlap in DuckDB
                            overlap_query = f'''
                                WITH set1 AS (SELECT DISTINCT "{c1}" AS val FROM "{t1}" WHERE "{c1}" IS NOT NULL),
                                     set2 AS (SELECT DISTINCT "{c2}" AS val FROM "{t2}" WHERE "{c2}" IS NOT NULL),
                                     intersected AS (SELECT val FROM set1 INTERSECT SELECT val FROM set2)
                                SELECT
                                    (SELECT COUNT(*) FROM intersected) * 1.0 / NULLIF((SELECT COUNT(*) FROM set1), 0) AS ratio1,
                                    (SELECT COUNT(*) FROM intersected) * 1.0 / NULLIF((SELECT COUNT(*) FROM set2), 0) AS ratio2
                            '''
                            overlap_row = con.execute(overlap_query).fetchone()
                            if not overlap_row or overlap_row[0] is None:
                                continue

                            r1, r2 = float(overlap_row[0]), float(overlap_row[1])
                            max_overlap = max(r1, r2)

                            if max_overlap >= 0.5:
                                # High confidence join key
                                confidence = 0.5 + (max_overlap * 0.5)
                                from_t, from_c = (t1, c1) if r1 >= r2 else (t2, c2)
                                to_t, to_c = (t2, c2) if r1 >= r2 else (t1, c1)

                                edge = RelationshipEdge(
                                    from_table=from_t,
                                    from_column=from_c,
                                    to_table=to_t,
                                    to_column=to_c,
                                    confidence=confidence,
                                    overlap_ratio=max_overlap,
                                    relationship_type="many-to-one" if max_overlap > 0.8 else "many-to-many",
                                )
                                edges.append(edge)

        finally:
            con.close()

        return [e.to_dict() for e in edges]
