-- App tables for Interview Coach (mirrors backend SQLAlchemy models)

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    name VARCHAR(120) NOT NULL DEFAULT 'User',
    avatar_url VARCHAR(512),
    facebook_id VARCHAR(64) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_facebook_id ON users (facebook_id);

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(64) NOT NULL,
    question_id VARCHAR(128) NOT NULL,
    question TEXT NOT NULL,
    video_storage_key VARCHAR(512),
    transcript TEXT,
    overall_score INTEGER NOT NULL DEFAULT 0,
    delivery_score INTEGER NOT NULL DEFAULT 0,
    communication_score INTEGER NOT NULL DEFAULT 0,
    technical_score INTEGER NOT NULL DEFAULT 0,
    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    llm_provider VARCHAR(32),
    vector_store VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_evaluations_user_id ON evaluations (user_id);
