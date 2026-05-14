// Alert event publisher — publishes AlertStateChanged with retry + dead letter queue
//
// Retries: up to 3 attempts with 1s linear backoff
// Dead letter: writes failed events to console.error (hook point for audit logging)
// Implements AlertEventPublisher interface from alert-repository.ts

import { AlertStatus } from './alert-model';
import type { AlertEventPublisher } from './alert-repository';

export interface EventBus {
  publish(topic: string, payload: object): Promise<void>;
}

export class AlertStateChangedPublisher implements AlertEventPublisher {
  private readonly maxRetries = 3;
  private readonly retryIntervalMs = 1000;

  constructor(private bus: EventBus) {}

  async publishAlertStateChanged(event: {
    alert_id: number;
    user_id: string;
    old_status: AlertStatus | null;
    new_status: AlertStatus;
    timestamp: Date;
  }): Promise<void> {
    const payload = { type: 'AlertStateChanged', ...event };

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        await this.bus.publish('alerts.state-changed', payload);
        return;
      } catch (e) {
        if (attempt === this.maxRetries) {
          this.writeDeadLetter(payload, e);
          throw e;
        }
        await this.sleep(this.retryIntervalMs * attempt);
      }
    }
  }

  private writeDeadLetter(payload: object, error: unknown): void {
    // Dead letter queue hook point — replace with actual DLQ infrastructure in production
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error(`[DLQ] AlertStateChanged publish failed: ${errorMsg}`, payload);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
