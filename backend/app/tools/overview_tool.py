"""Live table profiles and verified relationship evidence for dataset overviews."""
from typing import Any

import duckdb

from app.data.catalog import SemanticCatalogBuilder
from app.data.quality import QualityAuditor
from app.data.relationships import RelationshipDetector


class DatasetOverviewTool:
    def __init__(self, db_path: str, tables: list[str]) -> None:
        self.db_path = db_path
        self.tables = tables

    def execute(self) -> dict[str, Any]:
        con = duckdb.connect(self.db_path, read_only=True)
        tables: list[dict[str, Any]] = []
        queries: list[str] = []
        try:
            for table in self.tables:
                schema_sql = f'DESCRIBE "{table}"'
                count_sql = f'SELECT COUNT(*) FROM "{table}"'
                queries.extend([schema_sql, count_sql])
                schema = con.execute(schema_sql).fetchall()
                count = con.execute(count_sql).fetchone()
                profiles = []
                for column in schema:
                    name, dtype = str(column[0]), str(column[1])
                    sql = f'SELECT COUNT(*) FILTER (WHERE "{name}" IS NULL), COUNT(DISTINCT "{name}"), MIN("{name}"), MAX("{name}") FROM "{table}"'
                    queries.append(sql)
                    stats = con.execute(sql).fetchone()
                    assert stats is not None
                    top_sql = f'SELECT "{name}", COUNT(*) AS frequency FROM "{table}" WHERE "{name}" IS NOT NULL GROUP BY "{name}" ORDER BY frequency DESC LIMIT 3'
                    queries.append(top_sql)
                    top = con.execute(top_sql).fetchall()
                    profiles.append({"column":name,"type":dtype,"description":SemanticCatalogBuilder().infer_column_description(name,dtype),"null_count":stats[0],"distinct_count":stats[1],"min":str(stats[2]) if stats[2] is not None else None,"max":str(stats[3]) if stats[3] is not None else None,"top_values":[{"value":str(row[0]),"count":row[1]} for row in top]})
                quality = QualityAuditor().evaluate_table_quality(self.db_path,table)
                queries.extend(quality["sql_queries"])
                tables.append({"table":table,"row_count":int(count[0]) if count else 0,"column_count":len(schema),"columns":profiles,"quality_score":quality["score"],"quality_issues":quality["issues"]})
        finally:
            con.close()
        relationships = RelationshipDetector().detect_table_relationships(self.db_path,self.tables)
        return {"tables":tables,"relationships":relationships,"queries":queries}
