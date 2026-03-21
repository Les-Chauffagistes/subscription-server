-- CreateTable
CREATE TABLE "subscription_rates" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "sats_per_day" INTEGER NOT NULL,
    "valid_from" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "subscription_rates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subscriptions" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "pool_address" TEXT NOT NULL,
    "started_at" TIMESTAMPTZ,
    "expires_at" TIMESTAMPTZ,
    "status" TEXT NOT NULL DEFAULT 'inactive',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "subscriptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lightning_invoices" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "subscription_id" UUID NOT NULL,
    "opennode_charge_id" TEXT NOT NULL,
    "payment_request" TEXT NOT NULL,
    "amount_sats" BIGINT NOT NULL,
    "payer_address" TEXT,
    "rate_id" UUID NOT NULL,
    "sats_per_day" INTEGER NOT NULL,
    "duration_days" INTEGER NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "expires_at" TIMESTAMPTZ NOT NULL,
    "paid_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "lightning_invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subscription_payments" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "subscription_id" UUID NOT NULL,
    "invoice_id" UUID NOT NULL,
    "amount_sats" BIGINT NOT NULL,
    "duration_days" INTEGER NOT NULL,
    "extended_from" TIMESTAMPTZ NOT NULL,
    "extended_until" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "subscription_payments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "opennode_webhook_logs" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "opennode_charge_id" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "status" TEXT NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "error_message" TEXT,
    "received_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "opennode_webhook_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "subscription_rates_valid_from_idx" ON "subscription_rates"("valid_from");

-- CreateIndex
CREATE UNIQUE INDEX "subscriptions_pool_address_key" ON "subscriptions"("pool_address");

-- CreateIndex
CREATE INDEX "subscriptions_pool_address_idx" ON "subscriptions"("pool_address");

-- CreateIndex
CREATE INDEX "subscriptions_status_idx" ON "subscriptions"("status");

-- CreateIndex
CREATE INDEX "subscriptions_expires_at_idx" ON "subscriptions"("expires_at");

-- CreateIndex
CREATE UNIQUE INDEX "lightning_invoices_opennode_charge_id_key" ON "lightning_invoices"("opennode_charge_id");

-- CreateIndex
CREATE INDEX "lightning_invoices_opennode_charge_id_idx" ON "lightning_invoices"("opennode_charge_id");

-- CreateIndex
CREATE INDEX "lightning_invoices_subscription_id_idx" ON "lightning_invoices"("subscription_id");

-- CreateIndex
CREATE INDEX "lightning_invoices_payer_address_idx" ON "lightning_invoices"("payer_address");

-- CreateIndex
CREATE UNIQUE INDEX "subscription_payments_invoice_id_key" ON "subscription_payments"("invoice_id");

-- CreateIndex
CREATE INDEX "opennode_webhook_logs_opennode_charge_id_idx" ON "opennode_webhook_logs"("opennode_charge_id");

-- AddForeignKey
ALTER TABLE "lightning_invoices" ADD CONSTRAINT "lightning_invoices_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "subscriptions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "lightning_invoices" ADD CONSTRAINT "lightning_invoices_rate_id_fkey" FOREIGN KEY ("rate_id") REFERENCES "subscription_rates"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subscription_payments" ADD CONSTRAINT "subscription_payments_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "subscriptions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subscription_payments" ADD CONSTRAINT "subscription_payments_invoice_id_fkey" FOREIGN KEY ("invoice_id") REFERENCES "lightning_invoices"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
