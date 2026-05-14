// Tier gate — condition type access control with stale-while-revalidate cache
//
// Free users restricted to: price_above, price_below, price_crosses
// Premium users: unrestricted
// Cache: in-memory Map, TTL 5min, stale refresh 30min, event-driven invalidation

import { ConditionType, isTypeRestricted } from './alert-model';

export interface TierResolver {
  resolveTier(userId: string): Promise<'free' | 'premium'>;
}

interface CacheEntry {
  tier: 'free' | 'premium';
  expiresAt: number;    // fresh window
  staleUntil: number;   // stale-while-revalidate window
}

export class TierGate {
  private cache = new Map<string, CacheEntry>();
  private readonly ttlMs = 5 * 60 * 1000;        // 5 min fresh
  private readonly staleMs = 30 * 60 * 1000;      // 30 min stale window

  constructor(private resolver: TierResolver) {}

  async checkTierAccess(
    userId: string,
    conditionType: ConditionType,
  ): Promise<{ allowed: true } | { allowed: false; reason: string; upgradeUrl?: string }> {
    const tier = await this.resolveTier(userId);
    if (!isTypeRestricted(conditionType, tier)) {
      return { allowed: true };
    }
    return {
      allowed: false,
      reason: `Condition type '${conditionType}' requires premium tier`,
      upgradeUrl: '/upgrade',
    };
  }

  async resolveTier(userId: string): Promise<'free' | 'premium'> {
    const cached = this.cache.get(userId);
    const now = Date.now();

    // Fresh cache hit
    if (cached && now < cached.expiresAt) {
      return cached.tier;
    }

    // Stale cache hit — revalidate async (fire-and-forget)
    if (cached && now < cached.staleUntil) {
      this.refreshCache(userId).catch(() => { /* keep stale */ });
      return cached.tier;
    }

    return this.refreshCache(userId);
  }

  private async refreshCache(userId: string): Promise<'free' | 'premium'> {
    try {
      const tier = await this.resolver.resolveTier(userId);
      const now = Date.now();
      this.cache.set(userId, {
        tier,
        expiresAt: now + this.ttlMs,
        staleUntil: now + this.staleMs,
      });
      return tier;
    } catch {
      // Infrastructure failure — fall back to free (conservative)
      return 'free';
    }
  }

  invalidateTierCache(userId: string): void {
    this.cache.delete(userId);
  }

  clearTierCache(): void {
    this.cache.clear();
  }
}
