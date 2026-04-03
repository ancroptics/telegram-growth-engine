-- Migration 002: Add missing tables and columns

-- Platform settings table (used by admin_panel)
CREATE TABLE IF NOT EXISTS platform_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add i18n column to managed_channels
ALTER TABLE managed_channels ADD COLUMN IF NOT EXISTS welcome_messages_i18n JSONB DEFAULT '{}';

-- Add is_active column to managed_channels
ALTER TABLE managed_channels ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Daily stats table
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    joins INTEGER DEFAULT 0,
    leaves INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    UNIQUE(chat_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_stats_chat_date ON daily_stats(chat_id, date);
