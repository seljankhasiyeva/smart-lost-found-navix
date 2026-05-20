CREATE EXTENSION IF NOT EXISTS 'uuid-ossp';

CREATE TABLE IF NOT EXISTS items (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    status          VARCHAR(10) NOT NULL
                    CHECK (status IN ('lost', 'found')),
    user_text       TEXT        NOT NULL,
    image_path      TEXT,
    vlm_description JSONB,
    embedding       BYTEA,
    confidence      FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_status
    ON items(status);

CREATE INDEX IF NOT EXISTS idx_items_created
    ON items(created_at DESC);
