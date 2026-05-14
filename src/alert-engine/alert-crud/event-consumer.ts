// Alert event consumer — inbound event handlers for cache invalidation
//
// Registered handlers:
//   PremiumTierChanged → invalidate tier cache (TierGate)
//   PreferencesChanged → placeholder (preference cache TBD)
//
// Retries: up to 3 attempts with 1s interval per handler batch
// No handlers registered → ack (no-op)

import { TierGate } from './tier-gate';

export interface EventEnvelope {
  type: string;
  user_id: string;
  payload: Record<string, unknown>;
}

export type EventHandler = (envelope: EventEnvelope) => Promise<void>;
export type SubscriberId = string;

export class AlertEventConsumer {
  private handlers = new Map<string, Map<SubscriberId, EventHandler>>();
  private readonly maxRetries = 3;
  private readonly retryIntervalMs = 1000;

  constructor(private tierGate: TierGate) {
    // Register built-in handlers
    this.on('PremiumTierChanged', async (envelope) => {
      this.tierGate.invalidateTierCache(envelope.user_id);
    });
  }

  on(eventType: string, handler: EventHandler): SubscriberId {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Map());
    }
    const id = `${eventType}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    this.handlers.get(eventType)!.set(id, handler);
    return id;
  }

  unsubscribe(eventType: string, subscriberId: SubscriberId): boolean {
    return this.handlers.get(eventType)?.delete(subscriberId) ?? false;
  }

  async consume(
    envelope: EventEnvelope,
  ): Promise<{ ok: true } | { ok: false; attempts: number; error: string }> {
    const subs = this.handlers.get(envelope.type);
    if (!subs || subs.size === 0) {
      return { ok: true }; // no handler — ack and continue
    }

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        const promises = [...subs.values()].map((h) => h(envelope));
        await Promise.all(promises);
        return { ok: true };
      } catch (e) {
        if (attempt === this.maxRetries) {
          return {
            ok: false,
            attempts: attempt,
            error: e instanceof Error ? e.message : 'Unknown error',
          };
        }
        await this.sleep(this.retryIntervalMs);
      }
    }

    return { ok: false, attempts: this.maxRetries, error: 'Unexpected end of retry loop' };
  }

  subscriberCount(eventType?: string): number {
    if (eventType) {
      return this.handlers.get(eventType)?.size ?? 0;
    }
    let total = 0;
    for (const subs of this.handlers.values()) {
      total += subs.size;
    }
    return total;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
