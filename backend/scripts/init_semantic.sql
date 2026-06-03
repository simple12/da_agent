-- Phase 2 semantic metadata repository (Postgres schema: semantic)
DROP SCHEMA IF EXISTS semantic CASCADE;
CREATE SCHEMA semantic;

CREATE TABLE semantic.metrics (
    metric_id SERIAL PRIMARY KEY,
    metric_name VARCHAR(64) NOT NULL UNIQUE,
    metric_definition TEXT NOT NULL,
    metric_formula TEXT NOT NULL,
    aggregation_type VARCHAR(32) NOT NULL,
    business_owner VARCHAR(128) NOT NULL DEFAULT 'analytics'
);

CREATE TABLE semantic.dimensions (
    dimension_id SERIAL PRIMARY KEY,
    dimension_name VARCHAR(64) NOT NULL UNIQUE,
    table_name VARCHAR(64) NOT NULL,
    column_name VARCHAR(64) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    aliases TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE semantic.tables (
    table_id SERIAL PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE semantic.table_columns (
    column_id SERIAL PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL REFERENCES semantic.tables (table_name) ON DELETE CASCADE,
    column_name VARCHAR(64) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    UNIQUE (table_name, column_name)
);

CREATE TABLE semantic.joins (
    join_id SERIAL PRIMARY KEY,
    source_table VARCHAR(64) NOT NULL,
    target_table VARCHAR(64) NOT NULL,
    join_condition TEXT NOT NULL,
    join_type VARCHAR(16) NOT NULL DEFAULT 'INNER',
    UNIQUE (source_table, target_table, join_condition)
);

CREATE TABLE semantic.sample_queries (
    query_id SERIAL PRIMARY KEY,
    question_pattern TEXT NOT NULL,
    sql_template TEXT NOT NULL,
    metric_name VARCHAR(64) REFERENCES semantic.metrics (metric_name) ON DELETE SET NULL,
    description TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_semantic_dimensions_table ON semantic.dimensions (table_name);
CREATE INDEX idx_semantic_table_columns_table ON semantic.table_columns (table_name);
CREATE INDEX idx_semantic_joins_source ON semantic.joins (source_table);
CREATE INDEX idx_semantic_joins_target ON semantic.joins (target_table);
