-- TELEGRAM GROWTH ENGINE — COMPLETE DATABASE SCHEMA
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS channel_owners (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free',
    tier_expires_at TIMESTAMP,
    referrer_id BIGINT,
    referral_count INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS managed_channels (
    chat_id BIGINT PRIMARY KEY,
    chat_title VARCHAR(255),
    chat_type VARCHAR(50) DEFAULT 'channel',
    chat_username VARCHAR(255),
    owner_id BIGINT REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    member_count INT DEFAULT 0,
    total_approved INT DEFAULT 0,
    total_dms_sent INT DEFAULT 0,
    auto_approve BOOLEAN DEFAULT TRUE,
    welcome_dm_enabled BOOLEAN DEFAULT TRUE,
    welcome_message TEXT,
    welcome_media_type VARCHAR(20),
    welcome_media_file_id TEXT,
    drip_enabled BOOLEAN DEFAULT FALSE,
    drip_rate INT DEFAULT 50,
    drip_active_start INT DEFAULT 8,
    drip_active_end INT DEFAULT 23,
    force_subscribe_enabled BOOLEAN DEFAULT FALSE,
    force_subscribe_channels JSONB DEFAULT '[]',
    language VARCHAR(10) DEFAULT 'en',
    category VARCHAR(50),
    cross_promo_enabled BOOLEAN DEFAULT FALSE,
    watermark_enabled BOOLEAN DEFAULT FALSE,
    watermark_text VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS join_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL REFERENCES managed_channels(chat_id) ON DELETE CASCADE,
    user_full_name VARCHAR(255),
    user_username VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    approved_via VARCHAR(50),
    force_sub_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    UNIQUE(user_id, chat_id)
);

CREATE TABLE IF NOT EXISTS channel_stats (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES managed_channels(chat_id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    requests_received INT DEFAULT 0,
    requests_approved INT DEFAULT 0,
    requests_declined INT DEFAULT 0,
    dms_sent INT DEFAULT 0,
    dms_failed INT DEFAULT 0,
    UNIQUE(chat_id, date)
);

CREATE TABLE IF NOT EXISTS broadcasts (
    broadcast_id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    channel_id BIGINT,
    content_type VARCHAR(20) DEFAULT 'text',
    content TEXT,
    media_file_id TEXT,
    caption TEXT,
    target_segment VARCHAR(50) DEFAULT 'all',
    status VARCHAR(20) DEFAULT 'draft',
    scheduled_at TIMESTAMP,
    sent_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    blocked_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    content TEXT,
    media_file_id TEXT,
    caption TEXT,
    use_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(owner_id, name)
);

CREATE TABLE IF NOT EXISTS auto_post_schedules (
    schedule_id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    group_chat_id BIGINT NOT NULL,
    content TEXT,
    content_type VARCHAR(20) DEFAULT 'text',
    media_file_id TEXT,
    interval_minutes INT DEFAULT 60,
    is_active BOOLEAN DEFAULT TRUE,
    next_run_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_post_groups (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    chat_title VARCHAR(255),
    owner_id BIGINT NOT NULL REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chat_id, owner_id)
);

CREATE TABLE IF NOT EXISTS cloned_bots (
    id SERIAL PRIMARY KEY,
    owner_id BIGINT NOT NULL REFERENCES channel_owners(user_id) ON DELETE CASCADE,
    bot_token TEXT NOT NULL,
    bot_username VARCHAR(255),
    bot_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cross_promo_listings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES managed_channels(chat_id) ON DELETE CASCADE,
    owner_id BIGINT NOT NULL,
    category VARCHAR(50),
    description TEXT,
    member_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_join_requests_chat_status ON join_requests(chat_id, status);
CREATE INDEX IF NOT EXISTS idx_join_requests_user ON join_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_stats_date ON channel_stats(chat_id, date);
CREATE INDEX IF NOT EXISTS idx_broadcasts_owner ON broadcasts(owner_id);
CREATE INDEX IF NOT EXISTS idx_managed_channels_owner ON managed_channels(owner_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cross_promo_cat ON cross_promo_listings(category, is_active);
