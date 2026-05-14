// Alert limiter — free tier active alert count enforcement
//
// Free users: max 5 active alerts (status IN (active, paused))
// Premium users: unlimited
// Uses AlertRepository.countActive() for server-side enforcement

import { ALERT_FREE_LIMIT } from './alert-model';
import { AlertRepository } from './alert-repository';

export class AlertLimiter {
  constructor(private repo: AlertRepository) {}

  async checkLimit(
    userId: string,
    tier: 'free' | 'premium',
  ): Promise<{ allowed: true } | { allowed: false; reason: string; activeCount: number }> {
    if (tier === 'premium') {
      return { allowed: true };
    }

    const activeCount = await this.repo.countActive(userId);
    if (activeCount >= ALERT_FREE_LIMIT) {
      return {
        allowed: false,
        reason: `Free tier limit of ${ALERT_FREE_LIMIT} active alerts exceeded`,
        activeCount,
      };
    }

    return { allowed: true };
  }
}
