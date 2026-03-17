INSERT INTO subscription_rates (sats_per_day) VALUES (50);
INSERT INTO subscription_rates (sats_per_day, valid_from) VALUES (60, '2024-01-01');

INSERT INTO subscriptions (pool_address) VALUES ('bc1');
INSERT INTO subscriptions (pool_address, started_at) VALUES ('bc2', '2026-01-01');
INSERT INTO subscriptions (pool_address) VALUES ('bc3');