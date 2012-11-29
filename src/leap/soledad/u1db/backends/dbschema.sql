-- Database schema
CREATE TABLE transaction_log (
    generation INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL
);
CREATE TABLE document (
    doc_id TEXT PRIMARY KEY,
    doc_rev TEXT NOT NULL,
    content TEXT
);
CREATE TABLE document_fields (
    doc_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    value TEXT
);
CREATE INDEX document_fields_field_value_doc_idx
    ON document_fields(field_name, value, doc_id);

CREATE TABLE sync_log (
    replica_uid TEXT PRIMARY KEY,
    known_generation INTEGER,
    known_transaction_id TEXT
);
CREATE TABLE conflicts (
    doc_id TEXT,
    doc_rev TEXT,
    content TEXT,
    CONSTRAINT conflicts_pkey PRIMARY KEY (doc_id, doc_rev)
);
CREATE TABLE index_definitions (
    name TEXT,
    offset INT,
    field TEXT,
    CONSTRAINT index_definitions_pkey PRIMARY KEY (name, offset)
);
create index index_definitions_field on index_definitions(field);
CREATE TABLE u1db_config (
    name TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO u1db_config VALUES ('sql_schema', '0');
