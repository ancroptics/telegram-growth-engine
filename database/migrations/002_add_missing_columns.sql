-- Add missing columns referenced in code
ALTER TABLE managed_channels ADD COLUMN IF NOT EXISTS welcome_messages_i18n JSONB DEFAULT '{}';
