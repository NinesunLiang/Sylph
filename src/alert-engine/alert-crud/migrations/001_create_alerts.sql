-- Migration: 001_create_alerts
-- Creates alert configuration, condition, and history tables
-- Idempotent: IF NOT EXISTS guards against re-execution

BEGIN;

CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT        NOT NULL,
    symbol          TEXT        NOT NULL,
    condition_type  TEXT        NOT NULL CHECK (condition_type IN (
                        'price_above', 'price_below', 'price_crosses',
                        'rsi_above', 'rsi_below',
                        'macd_cross', 'macd_divergence',
                        'sma_cross', 'ema_cross',
                        'bollinger_break', 'stoch_k_cross',
                        'atr_break', 'ichimoku_break',
                        'volume_profile', 'fibonacci_retrace',
                        'head_shoulders', 'double_top', 'double_bottom',
                        'triangle_break', 'wedge_break', 'flag_pattern'
                    )),
    threshold       NUMERIC     NOT NULL CHECK (threshold > 0),
    channels        TEXT[]      NOT NULL CHECK (array_length(channels, 1) > 0),
    status          TEXT        NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'paused', 'triggered', 'expired')),
    version         INTEGER     NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts (user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts (symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_user_status ON alerts (user_id, status);

CREATE TABLE IF NOT EXISTS alert_conditions (
    id              BIGSERIAL PRIMARY KEY,
    alert_id        BIGINT      NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    condition_type  TEXT        NOT NULL,
    params          JSONB       NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_conditions_alert_id ON alert_conditions (alert_id);

CREATE TABLE IF NOT EXISTS alert_history (
    id              BIGSERIAL PRIMARY KEY,
    alert_id        BIGINT      NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    price           NUMERIC     NOT NULL,
    notification_status TEXT    DEFAULT 'pending'
                        CHECK (notification_status IN ('pending', 'delivered', 'failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history (alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_triggered_at ON alert_history (triggered_at);

COMMIT;
