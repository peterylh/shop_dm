#!/usr/bin/env python3
"""
将 sibling 目录下的 dbt 项目转换为当前仓库可执行的 finance_analytics 项目结构。

输出:
  - finance_analytics/ddl/*.sql
  - finance_analytics/tasks/*.sql
  - finance_analytics/schema.yaml
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DBT_ROOT = Path(__file__).resolve().parents[2] / "finance_analytics_dbt"
DB_NAME = "finance_analytics_dm"
SUPPORTED_MODEL_TARGETS = {
    "ads_customer_by_age_group",
    "ads_customer_by_geography",
    "ads_customer_by_segment",
    "ads_product_summary",
    "dim_account",
    "dim_agent",
    "dim_campaign",
    "dim_customer",
    "dim_date",
    "dim_economic_indicators",
    "dim_location",
    "dim_merchant",
    "dim_product",
    "dwd_account_events",
    "dwd_accounts",
    "dwd_atm_locations",
    "dwd_branch_locations",
    "dwd_credit_applications",
    "dwd_customer_interactions",
    "dwd_customer_segments_history",
    "dwd_customers",
    "dwd_economic_indicators",
    "dwd_fraud_alerts",
    "dwd_loan_payments",
    "dwd_marketing_campaigns",
    "dwd_merchants",
    "dwd_products",
    "dwd_regulatory_reports",
    "dwd_risk_assessments",
    "dwd_transactions",
    "dws_account_daily_snapshot",
    "dws_account_events",
    "dws_credit_applications",
    "dws_customer_interactions",
    "dws_customer_monthly_summary",
    "dws_customer_segment_history",
    "dws_fraud_alerts",
    "dws_loan_payments",
    "dws_marketing_campaigns",
    "dws_regulatory_reports",
    "dws_risk_assessments",
    "dws_transactions",
}
PRESERVE_EXISTING_TASKS = {"dim_agent", "dim_date", "dwd_accounts", "dws_transactions"}
PRESERVE_EXISTING_DDLS = {
    "dim_agent",
    "dim_location",
    "dwd_account_events",
    "dwd_atm_locations",
    "dwd_branch_locations",
    "dwd_customer_segments_history",
    "dwd_regulatory_reports",
    "dwd_risk_assessments",
    "dws_transactions",
}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def iter_model_files(dbt_root: Path) -> list[Path]:
    return sorted((dbt_root / "models").rglob("*.sql"))


def load_source_tables(dbt_root: Path) -> dict[str, dict[str, Any]]:
    source_cfg = load_yaml(dbt_root / "models" / "ingestion" / "sources.yml")
    tables: dict[str, dict[str, Any]] = {}
    for source in source_cfg.get("sources", []):
        for table in source.get("tables", []):
            tables[table["name"]] = table
    return tables


def load_model_meta(dbt_root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for schema_path in sorted((dbt_root / "models").rglob("schema.yml")):
        data = load_yaml(schema_path)
        for model in data.get("models", []):
            result[model["name"]] = model
    return result


def load_dbt_vars(dbt_root: Path) -> dict[str, Any]:
    cfg = load_yaml(dbt_root / "dbt_project.yml")
    return cfg.get("vars", {})


def target_name_for_source(source_name: str) -> str:
    return f"ods_{source_name}"


def target_name_for_model(model_name: str) -> str:
    if model_name.startswith("stg_"):
        return f"dwd_{model_name[4:]}"
    if model_name.startswith("dim_"):
        return model_name
    if model_name.startswith("fact_"):
        return f"dws_{model_name[5:]}"
    if model_name.startswith("analytics_"):
        return f"ads_{model_name[10:]}"
    return model_name


def build_name_mapping(
    source_tables: dict[str, dict[str, Any]],
    model_names: list[str],
) -> dict[str, str]:
    mapping = {name: target_name_for_source(name) for name in source_tables}
    for name in model_names:
        mapping[name] = target_name_for_model(name)
    return mapping


def is_supported_model(model_name: str) -> bool:
    return target_name_for_model(model_name) in SUPPORTED_MODEL_TARGETS


def sql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")


def is_datetime_name(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in {"load_time", "last_updated", "updated_at", "created_at", "etl_time"}
        or lowered.endswith("_at")
        or lowered.endswith("_time")
        or lowered.endswith("_timestamp")
        or lowered.endswith("_date")
        or lowered in {"date", "date_actual", "snapshot_date", "open_date", "close_date"}
    )


def infer_column_type(column_name: str) -> str:
    name = column_name.lower()
    integer_names = {
        "age",
        "transaction_year",
        "transaction_month",
        "transaction_day",
        "transaction_hour",
        "interaction_year",
        "interaction_month",
        "year",
        "quarter",
        "month",
        "week_of_year",
        "day_of_year",
        "day_of_week",
        "hour_of_day",
        "number_of_dependents",
        "days_late",
        "processing_days",
        "account_age_months",
        "tenure_months",
        "tenure_days",
        "duration_minutes",
        "resolution_days",
        "campaign_duration_days",
        "daily_transaction_limit",
        "avg_daily_transactions",
        "num_accounts",
        "years_as_customer",
        "branch_visits_last_90d",
        "online_logins_last_90d",
        "products_held",
        "velocity_24h",
        "total_accounts",
        "active_accounts",
        "closed_accounts",
        "dormant_accounts",
        "past_due_accounts",
        "near_limit_accounts",
        "total_transactions",
        "payment_id",
        "application_id",
        "customer_id",
        "product_id",
        "merchant_id",
        "account_id",
        "branch_id",
        "atm_id",
        "interaction_id",
        "campaign_id",
        "alert_id",
        "assessment_id",
        "event_id",
        "report_id",
        "segment_history_id",
        "transaction_id",
    }
    text_suffixes = (
        "_name",
        "_category",
        "_segment",
        "_tier",
        "_type",
        "_type_desc",
        "_status",
        "_reason",
        "_channel",
        "_model",
        "_level",
        "_group",
        "_desc",
        "_notes",
    )
    if name.endswith("_key"):
        if name.endswith("_natural_key"):
            return "BIGINT"
        return "CHAR(32)"
    if name.endswith(text_suffixes):
        return "STRING"
    if name.startswith("is_") or name.startswith("has_") or name.endswith("_flag"):
        return "BOOLEAN"
    if name in integer_names or name.endswith("_count") or name.startswith("num_"):
        return "BIGINT"
    if is_datetime_name(name):
        return "DATETIME"
    if any(
        token in name
        for token in (
            "amount",
            "balance",
            "rate",
            "ratio",
            "score",
            "price",
            "cost",
            "pct",
            "volume",
            "yield",
            "fee",
            "income",
            "limit",
            "value",
            "latitude",
            "longitude",
        )
    ):
        return "DECIMAL(18,4)"
    return "STRING"


def quote_identifier(name: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return f"`{name}`"


def strip_config_block(sql: str) -> str:
    sql = re.sub(r"\{\{\s*config\((?:.|\n)*?\)\s*\}\}\s*", "", sql, count=1)
    sql = re.sub(r"\{#(?:.|\n)*?#\}", "", sql)
    return sql.strip()


def replace_source_and_ref(sql: str, mapping: dict[str, str]) -> str:
    def source_repl(match: re.Match[str]) -> str:
        table = match.group(2)
        return f"{DB_NAME}.{mapping[table]}"

    def ref_repl(match: re.Match[str]) -> str:
        model = match.group(1)
        return f"{DB_NAME}.{mapping[model]}"

    sql = re.sub(
        r"\{\{\s*source\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)\s*\}\}",
        source_repl,
        sql,
    )
    sql = re.sub(r"\{\{\s*ref\(\s*'([^']+)'\s*\)\s*\}\}", ref_repl, sql)
    return sql


def replace_vars(sql: str, dbt_vars: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = dbt_vars[key]
        if isinstance(value, str):
            return f"'{sql_escape(value)}'"
        return str(value)

    return re.sub(r"\{\{\s*var\(\s*'([^']+)'\s*\)\s*\}\}", repl, sql)


def build_surrogate_key_sql(arg_list: str) -> str:
    expressions = ast.literal_eval(arg_list)
    parts = []
    for expr in expressions:
        cleaned = expr.strip()
        if re.match(r"(?is)^cast\(.+\bas\s+string\)$", cleaned):
            string_expr = cleaned
        else:
            string_expr = f"CAST({cleaned} AS STRING)"
        parts.append(f"COALESCE({string_expr}, '_dbt_null_')")
    return f"MD5(CONCAT_WS('||', {', '.join(parts)}))"


def replace_surrogate_keys(sql: str) -> str:
    pattern = re.compile(
        r"\{\{\s*dbt_utils\.generate_surrogate_key\((\[[^\]]*\])\)\s*\}\}",
        re.DOTALL,
    )
    return pattern.sub(lambda m: build_surrogate_key_sql(m.group(1)), sql)


def replace_date_spine(sql: str) -> str:
    pattern = re.compile(
        r"\{\{\s*dbt_utils\.date_spine\((?:.|\n)*?start_date=\"cast\('([^']+)' as date\)\"(?:.|\n)*?end_date=\"cast\('([^']+)' as date\)\"(?:.|\n)*?\)\s*\}\}",
        re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        start_date = match.group(1)
        end_date = match.group(2)
        digits = " UNION ALL ".join(f"SELECT {i} AS n" for i in range(10))
        return f"""
SELECT
    DATE_ADD(CAST('{start_date}' AS DATE), INTERVAL (o.n + t.n * 10 + h.n * 100 + th.n * 1000) DAY) AS date_day
FROM ({digits}) o
CROSS JOIN ({digits}) t
CROSS JOIN ({digits}) h
CROSS JOIN ({digits}) th
WHERE DATE_ADD(CAST('{start_date}' AS DATE), INTERVAL (o.n + t.n * 10 + h.n * 100 + th.n * 1000) DAY) <= CAST('{end_date}' AS DATE)
""".strip()

    return pattern.sub(repl, sql)


def remove_incremental_blocks(sql: str) -> str:
    sql = re.sub(r"\{%\s*if\s+is_incremental\(\)\s*%\}(?:.|\n)*?\{%\s*endif\s*%\}", "", sql)
    return sql.replace("{{ this }}", "CURRENT_DATE")


def replace_pg_casts(sql: str) -> str:
    sql = sql.replace("'9999-12-31'::TIMESTAMP", "CAST('9999-12-31' AS DATETIME)")

    simple_casts = {
        "int": "BIGINT",
        "varchar": "STRING",
        "boolean": "BOOLEAN",
        "timestamp": "DATETIME",
        "date": "DATE",
        "float": "DOUBLE",
    }
    for cast_type, target_type in simple_casts.items():
        sql = re.sub(
            rf"\(([^()\n]+)\)::\s*{cast_type}\b",
            rf"CAST((\1) AS {target_type})",
            sql,
            flags=re.IGNORECASE,
        )
        sql = re.sub(
            rf"([A-Za-z_][A-Za-z0-9_\.]*)::\s*{cast_type}\b",
            rf"CAST(\1 AS {target_type})",
            sql,
            flags=re.IGNORECASE,
        )

    for cast_type in ("NUMERIC", "numeric"):
        sql = re.sub(
            rf"\(([^()\n]+)\)::\s*{cast_type}\b",
            r"CAST((\1) AS DECIMAL(18,4))",
            sql,
        )
        sql = re.sub(
            rf"([A-Za-z_][A-Za-z0-9_\.]*)::\s*{cast_type}\b",
            r"CAST(\1 AS DECIMAL(18,4))",
            sql,
        )
    return sql


def replace_age_expressions(sql: str) -> str:
    sql = re.sub(
        r"YEAR\(AGE\((.+?),\s*([^)]+)\)\)\s*\*\s*12\s*\+\s*MONTH\(AGE\(\1,\s*\2\)\)",
        r"TIMESTAMPDIFF(MONTH, \2, \1)",
        sql,
    )
    sql = re.sub(
        r"EXTRACT\(YEAR FROM AGE\(([^,]+), ([^)]+)\)\)\s*\*\s*12\s*\+\s*EXTRACT\(MONTH FROM AGE\(\1, \2\)\)",
        r"TIMESTAMPDIFF(MONTH, \2, \1)",
        sql,
    )
    sql = re.sub(
        r"EXTRACT\(YEAR FROM AGE\(CURRENT_DATE, ([^)]+)\)\)",
        r"TIMESTAMPDIFF(YEAR, \1, CURRENT_DATE)",
        sql,
    )
    return sql


def replace_extracts(sql: str) -> str:
    sql = re.sub(r"EXTRACT\(YEAR FROM ([^)]+)\)", r"YEAR(\1)", sql)
    sql = re.sub(r"EXTRACT\(MONTH FROM ([^)]+)\)", r"MONTH(\1)", sql)
    sql = re.sub(r"EXTRACT\(DAY FROM ([^)]+)\)", r"DAY(\1)", sql)
    sql = re.sub(r"EXTRACT\(HOUR FROM ([^)]+)\)", r"HOUR(\1)", sql)
    sql = re.sub(r"EXTRACT\(QUARTER FROM ([^)]+)\)", r"QUARTER(\1)", sql)
    sql = re.sub(r"EXTRACT\(WEEK FROM ([^)]+)\)", r"WEEKOFYEAR(\1)", sql)
    sql = re.sub(r"EXTRACT\(DOY FROM ([^)]+)\)", r"DAYOFYEAR(\1)", sql)
    sql = re.sub(r"EXTRACT\(DOW FROM ([^)]+)\)", r"(DAYOFWEEK(\1) - 1)", sql)
    return sql


def replace_to_char(sql: str) -> str:
    sql = re.sub(r"TO_CHAR\(([^,]+),\s*'YYYY-MM'\)", r"DATE_FORMAT(\1, '%Y-%m')", sql)
    sql = re.sub(r"TO_CHAR\(([^,]+),\s*'YYYY-Q'\)", r"CONCAT(YEAR(\1), '-Q', QUARTER(\1))", sql)
    sql = re.sub(r"TO_CHAR\(([^,]+),\s*'Day'\)", r"DAYNAME(\1)", sql)
    sql = re.sub(r"TO_CHAR\(([^,]+),\s*'Month'\)", r"MONTHNAME(\1)", sql)
    return sql


def replace_date_math(sql: str) -> str:
    sql = re.sub(
        r"EXTRACT\(DAY FROM \(CAST\(([^)]+) AS DATETIME\) - CAST\(([^)]+) AS DATETIME\)\)\)",
        r"DATEDIFF(\1, \2)",
        sql,
    )
    sql = re.sub(
        r"CAST\(([^)]+) AS DATE\)\s*-\s*CURRENT_DATE",
        r"DATEDIFF(\1, CURRENT_DATE)",
        sql,
    )
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*CAST\(([^)]+) AS DATE\)",
        r"DATEDIFF(CURRENT_DATE, \1)",
        sql,
    )
    sql = re.sub(
        r"CAST\(([^)]+) AS DATE\)\s*-\s*CAST\(([^)]+) AS DATE\)",
        r"DATEDIFF(\1, \2)",
        sql,
    )
    sql = re.sub(
        r"EXTRACT\(EPOCH FROM \(CURRENT_TIMESTAMP - ([^)]+)\)\)\s*/\s*60",
        r"TIMESTAMPDIFF(MINUTE, \1, CURRENT_TIMESTAMP)",
        sql,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s*-\s*INTERVAL\s*'([0-9]+)\s+hour'",
        r"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 HOUR)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s*-\s*INTERVAL\s*'([0-9]+)\s+hours'",
        r"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 HOUR)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s*-\s*INTERVAL\s*'([0-9]+)\s+day'",
        r"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 DAY)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s*-\s*INTERVAL\s*'([0-9]+)\s+days'",
        r"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 DAY)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s*-\s*INTERVAL\s*'([0-9]+)\s+minutes?'",
        r"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 MINUTE)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*INTERVAL\s*'([0-9]+)\s+day'",
        r"DATE_SUB(CURRENT_DATE, INTERVAL \1 DAY)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*INTERVAL\s*'([0-9]+)\s+days'",
        r"DATE_SUB(CURRENT_DATE, INTERVAL \1 DAY)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*INTERVAL\s*'([0-9]+)\s+year'",
        r"DATE_SUB(CURRENT_DATE, INTERVAL \1 YEAR)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_DATE\s*-\s*INTERVAL\s*'([0-9]+)\s+years'",
        r"DATE_SUB(CURRENT_DATE, INTERVAL \1 YEAR)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"DATE_TRUNC\('hour',\s*CURRENT_TIMESTAMP\)",
        "DATE_FORMAT(CURRENT_TIMESTAMP, '%Y-%m-%d %H:00:00')",
        sql,
    )
    sql = re.sub(
        r"DATE_TRUNC\('hour',\s*DATE_SUB\(CURRENT_TIMESTAMP,\s*INTERVAL\s*([0-9]+)\s*DAY\)\)",
        r"DATE_FORMAT(DATE_SUB(CURRENT_TIMESTAMP, INTERVAL \1 DAY), '%Y-%m-%d %H:00:00')",
        sql,
    )
    sql = re.sub(
        r"DATE_TRUNC\('month',\s*([^)]+)\)",
        r"STR_TO_DATE(DATE_FORMAT(\1, '%Y-%m-01'), '%Y-%m-%d')",
        sql,
    )
    sql = re.sub(
        r"\(STR_TO_DATE\(DATE_FORMAT\(([^,]+), '%Y-%m-01'\), '%Y-%m-%d'\)\s*\+\s*INTERVAL\s*'1 month - 1 day'\)(?:\s+AS DATE)?",
        r"LAST_DAY(CAST(\1 AS DATE))",
        sql,
    )
    sql = re.sub(
        r"DATE_TRUNC\('quarter',\s*([^)]+)\)(?:\s+AS DATE)?",
        r"MAKEDATE(YEAR(CAST(\1 AS DATE)), 1) + INTERVAL (QUARTER(CAST(\1 AS DATE)) - 1) QUARTER",
        sql,
    )
    sql = re.sub(
        r"\(DATE_TRUNC\('quarter',\s*([^)]+)\)\s*\+\s*INTERVAL\s*'3 months - 1 day'\)(?:\s+AS DATE)?",
        r"DATE_SUB(MAKEDATE(YEAR(CAST(\1 AS DATE)), 1) + INTERVAL QUARTER(CAST(\1 AS DATE)) QUARTER, INTERVAL 1 DAY)",
        sql,
    )
    sql = re.sub(
        r"DATE_TRUNC\('year',\s*([^)]+)\)(?:\s+AS DATE)?",
        r"MAKEDATE(YEAR(CAST(\1 AS DATE)), 1)",
        sql,
    )
    sql = re.sub(
        r"\(DATE_TRUNC\('year',\s*([^)]+)\)\s*\+\s*INTERVAL\s*'1 year - 1 day'\)(?:\s+AS DATE)?",
        r"DATE_SUB(MAKEDATE(YEAR(CAST(\1 AS DATE)) + 1, 1), INTERVAL 1 DAY)",
        sql,
    )
    return sql


def replace_filter_clauses(sql: str) -> str:
    sql = re.sub(
        r"COUNT\(\*\)\s+FILTER\s+\(\s*WHERE\s+([\s\S]*?)\)",
        r"SUM(CASE WHEN \1 THEN 1 ELSE 0 END)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"SUM\(([^)]+)\)\s+FILTER\s+\(\s*WHERE\s+([\s\S]*?)\)",
        r"SUM(CASE WHEN \2 THEN \1 ELSE 0 END)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"AVG\(([^)]+)\)\s+FILTER\s+\(\s*WHERE\s+([\s\S]*?)\)",
        r"AVG(CASE WHEN \2 THEN \1 END)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"COUNT\(DISTINCT\s+([^)]+)\)\s+FILTER\s+\(\s*WHERE\s+([\s\S]*?)\)",
        r"COUNT(DISTINCT CASE WHEN \2 THEN \1 END)",
        sql,
        flags=re.IGNORECASE,
    )
    return sql


def replace_identifier_quotes(sql: str) -> str:
    return re.sub(r'"([0-9][A-Za-z0-9_]*)"', r"`\1`", sql)


def final_cleanup(sql: str) -> str:
    sql = sql.replace("CURRENT_DATE()", "CURRENT_DATE")
    sql = re.sub(r"CAST\(CAST\(([^()]+)\s+AS\s+STRING\)\)", r"CAST(\1 AS STRING)", sql, flags=re.IGNORECASE)
    sql = re.sub(
        r"([A-Za-z_][A-Za-z0-9_\.]*)\s+AS\s+(DATETIME|DATE|DOUBLE|BIGINT|STRING)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"CAST(\1 AS \2) AS \3",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"DAY\(\(\s*([A-Za-z_][A-Za-z0-9_\.]*)\s+AS\s+DATETIME\s*-\s*([A-Za-z_][A-Za-z0-9_\.]*)\s+AS\s+DATETIME\s*\)\)",
        r"DATEDIFF(CAST(\1 AS DATE), CAST(\2 AS DATE))",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"(SUM\(CASE WHEN [^)]+ END\))\s+AS\s+DOUBLE\s*/\s*COUNT\(\*\)",
        r"CAST(\1 AS DOUBLE) / COUNT(*)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"SUMCAST\(\((.*?)\)\s+AS\s+DOUBLE\)",
        r"CAST(SUM(\1) AS DOUBLE)",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    sql = re.sub(r"WHERE\s+HOUR\(([^)]+)\)\s+BETWEEN\s+22\s+AND\s+6", r"WHERE (HOUR(\1) >= 22 OR HOUR(\1) <= 6)", sql)
    sql = re.sub(r"WHEN HOUR\(([^)]+)\)\s+BETWEEN\s+22\s+AND\s+6 THEN", r"WHEN (HOUR(\1) >= 22 OR HOUR(\1) <= 6) THEN", sql)
    sql = re.sub(r"ROUND\(\s*CAST\(([^)]+)\s+AS\s+DECIMAL\(18,4\)\)\s*,\s*([0-9]+)\)", r"ROUND(\1, \2)", sql)
    sql = re.sub(r"NULLIF\(([^,]+),\s*CAST\(([^)]+)\)\s+AS\s+DECIMAL\(18,4\)\)\)", r"NULLIF(\1, \2)", sql)
    sql = re.sub(r"SUM\(([^)]+)CAST\(END\)\s+AS\s+DECIMAL\(18,4\)\)", r"SUM(\1END)", sql)
    sql = re.sub(r"\n{3,}", "\n\n", sql)
    if not sql.endswith("\n"):
        sql += "\n"
    return sql


def convert_sql(sql: str, mapping: dict[str, str], dbt_vars: dict[str, Any]) -> str:
    sql = strip_config_block(sql)
    sql = replace_source_and_ref(sql, mapping)
    sql = replace_vars(sql, dbt_vars)
    sql = replace_surrogate_keys(sql)
    sql = replace_date_spine(sql)
    sql = remove_incremental_blocks(sql)
    sql = replace_pg_casts(sql)
    sql = replace_age_expressions(sql)
    sql = replace_extracts(sql)
    sql = replace_to_char(sql)
    sql = replace_date_math(sql)
    sql = replace_filter_clauses(sql)
    sql = replace_identifier_quotes(sql)
    sql = final_cleanup(sql)
    return sql


def infer_columns_from_sql(sql: str) -> list[str]:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    upper_sql = sql.upper()
    select_pos = upper_sql.rfind("SELECT")
    from_pos = upper_sql.rfind("\nFROM ")
    if select_pos == -1 or from_pos == -1 or from_pos <= select_pos:
        return []
    select_body = sql[select_pos + len("SELECT"):from_pos]
    if select_body.strip() == "*":
        from_line = sql[from_pos:].splitlines()[0]
        match = re.search(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)\b", from_line, re.IGNORECASE)
        if match:
            cte_name = match.group(1)
            cte_sql = extract_cte_sql(sql, cte_name)
            if cte_sql:
                return infer_columns_from_sql(cte_sql)
    fields: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in select_body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        fields.append("".join(current).strip())

    result = []
    for field in fields:
        alias_match = re.search(r"\bAS\s+(`[^`]+`|[A-Za-z_][A-Za-z0-9_]*)\s*$", field, re.IGNORECASE)
        if alias_match:
            result.append(alias_match.group(1).strip("`"))
            continue
        bare = field.split(".")[-1].strip()
        if bare and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", bare):
            result.append(bare)
    return result


def extract_cte_sql(sql: str, cte_name: str) -> str | None:
    pattern = re.compile(rf"\b{re.escape(cte_name)}\s+AS\s*\(", re.IGNORECASE)
    match = pattern.search(sql)
    if not match:
        return None

    start = match.end()
    depth = 1
    idx = start
    while idx < len(sql) and depth > 0:
        ch = sql[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        idx += 1

    if depth != 0:
        return None
    return sql[start:idx - 1]


def collect_output_columns(
    model_meta: dict[str, dict[str, Any]],
    source_tables: dict[str, dict[str, Any]],
    name: str,
    fallback_sql: str | None = None,
) -> list[str]:
    if name in source_tables:
        cols = [col["name"] for col in source_tables[name].get("columns", [])]
        if "load_time" not in cols:
            cols.append("load_time")
        return cols
    if fallback_sql:
        inferred = infer_columns_from_sql(fallback_sql)
        if inferred:
            return inferred
    if name in model_meta:
        return [col["name"] for col in model_meta[name].get("columns", [])]
    raise KeyError(f"unable to resolve output columns for {name}")


def render_ddl(table_name: str, columns: list[str]) -> str:
    column_types = {col: infer_column_type(col) for col in columns}
    key_candidates = [quote_identifier(columns[0])]
    key_columns = {columns[0]}
    for col in key_columns:
        if column_types.get(col) == "STRING":
            column_types[col] = "VARCHAR(255)"
    column_defs = []
    for col in columns:
        column_defs.append(f"    {quote_identifier(col)} {column_types[col]} NULL")
    key_cols = key_candidates[0]
    hash_col = key_candidates[0]
    return (
        f"DROP TABLE IF EXISTS {DB_NAME}.{table_name};\n"
        f"CREATE TABLE IF NOT EXISTS {DB_NAME}.{table_name} (\n"
        + ",\n".join(column_defs)
        + f"\n) ENGINE=OLAP\n"
        + f"DUPLICATE KEY({key_cols})\n"
        + f"DISTRIBUTED BY HASH({hash_col}) BUCKETS 1\n"
        + 'PROPERTIES (\n    "replication_num" = "1"\n);\n'
    )


def render_task(table_name: str, converted_sql: str) -> str:
    return (
        f"-- Auto-generated from dbt model\n"
        f"TRUNCATE TABLE {DB_NAME}.{table_name};\n\n"
        f"INSERT INTO {DB_NAME}.{table_name}\n"
        f"{converted_sql.rstrip()};\n"
    )


def render_schema_yaml(model_targets: list[str]) -> str:
    payload = {
        "version": 2,
        "models": [
            {
                "name": name,
                "config": {"materialized": "full"},
            }
            for name in model_targets
        ],
    }
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def prune_generated_files() -> None:
    for directory in (PROJECT_DIR / "tasks", PROJECT_DIR / "ddl"):
        for path in directory.glob("*.sql"):
            stem = path.stem
            if stem.startswith("ods_"):
                continue
            if stem not in SUPPORTED_MODEL_TARGETS:
                path.unlink()


def main() -> None:
    dbt_root = DEFAULT_DBT_ROOT
    source_tables = load_source_tables(dbt_root)
    model_meta = load_model_meta(dbt_root)
    dbt_vars = load_dbt_vars(dbt_root)
    model_files = [path for path in iter_model_files(dbt_root) if is_supported_model(path.stem)]
    mapping = build_name_mapping(source_tables, [path.stem for path in model_files])
    prune_generated_files()

    for source_name in sorted(source_tables):
        target_name = mapping[source_name]
        columns = collect_output_columns(model_meta, source_tables, source_name)
        ddl_path = PROJECT_DIR / "ddl" / f"{target_name}.sql"
        ddl_path.write_text(render_ddl(target_name, columns), encoding="utf-8")

    model_targets: list[str] = []
    for model_path in model_files:
        model_name = model_path.stem
        target_name = mapping[model_name]
        model_targets.append(target_name)

        converted_sql = convert_sql(model_path.read_text(encoding="utf-8"), mapping, dbt_vars)
        ddl_columns = collect_output_columns(model_meta, source_tables, model_name, converted_sql)
        task_path = PROJECT_DIR / "tasks" / f"{target_name}.sql"

        ddl_path = PROJECT_DIR / "ddl" / f"{target_name}.sql"
        if not (target_name in PRESERVE_EXISTING_DDLS and ddl_path.exists()):
            ddl_path.write_text(render_ddl(target_name, ddl_columns), encoding="utf-8")
        if target_name in PRESERVE_EXISTING_TASKS and task_path.exists():
            continue
        task_path.write_text(render_task(target_name, converted_sql), encoding="utf-8")

    (PROJECT_DIR / "schema.yaml").write_text(
        render_schema_yaml(sorted(model_targets)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
