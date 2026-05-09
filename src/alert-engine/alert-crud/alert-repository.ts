// Alert CRUD — PostgreSQL repository
// Uses pg (node-postgres) with parameterized queries

import { Pool, PoolClient } from 'pg';
import {
  Alert, AlertCondition, CreateAlertInput, UpdateAlertInput, AlertListFilter,
  ALERT_FREE_LIMIT, ConditionType, AlertStatus,
} from './alert-model';

export class AlertRepository {
  constructor(private pool: Pool) {}

  // ---------- create ----------

  async create(input: CreateAlertInput): Promise<Alert> {
    this.validateCreate(input);

    const sql = `
      INSERT INTO alerts (user_id, symbol, condition_type, threshold, channels, status)
      VALUES ($1, $2, $3, $4, $5, 'active')
      RETURNING id, user_id, symbol, condition_type, threshold,
                channels, status, version, created_at, updated_at
    `;
    const res = await this.pool.query<Alert>(sql, [
      input.user_id, input.symbol, input.condition_type,
      input.threshold, input.channels,
    ]);
    return res.rows[0];
  }

  async countActive(userId: string): Promise<number> {
    const sql = `SELECT COUNT(*) AS cnt FROM alerts
                 WHERE user_id = $1 AND status IN ('active','paused')`;
    const res = await this.pool.query<{ cnt: string }>(sql, [userId]);
    return parseInt(res.rows[0].cnt, 10);
  }

  // ---------- read ----------

  async getById(alertId: number): Promise<Alert | null> {
    const sql = `SELECT * FROM alerts WHERE id = $1`;
    const res = await this.pool.query<Alert>(sql, [alertId]);
    return res.rows[0] ?? null;
  }

  async list(filter: AlertListFilter): Promise<Alert[]> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let idx = 1;

    if (filter.user_id) {
      conditions.push(`user_id = $${idx++}`);
      params.push(filter.user_id);
    }
    if (filter.status) {
      conditions.push(`status = $${idx++}`);
      params.push(filter.status);
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    const limit = Math.min(filter.limit ?? 20, 100);
    const offset = ((filter.page ?? 1) - 1) * limit;

    const sql = `SELECT * FROM alerts ${where}
                 ORDER BY created_at DESC LIMIT $${idx++} OFFSET $${idx++}`;
    params.push(limit, offset);

    const res = await this.pool.query<Alert>(sql, params);
    return res.rows;
  }

  // ---------- update (optimistic lock) ----------

  async update(alertId: number, input: UpdateAlertInput): Promise<Alert | null> {
    const sets: string[] = [];
    const params: unknown[] = [];
    let idx = 1;

    if (input.symbol !== undefined) {
      sets.push(`symbol = $${idx++}`);
      params.push(input.symbol);
    }
    if (input.condition_type !== undefined) {
      sets.push(`condition_type = $${idx++}`);
      params.push(input.condition_type);
    }
    if (input.threshold !== undefined) {
      sets.push(`threshold = $${idx++}`);
      params.push(input.threshold);
    }
    if (input.channels !== undefined) {
      sets.push(`channels = $${idx++}`);
      params.push(input.channels);
    }
    if (input.status !== undefined) {
      this.validateStatusTransition(alertId, input.status);
      sets.push(`status = $${idx++}`);
      params.push(input.status);
    }

    sets.push(`version = version + 1, updated_at = NOW()`);

    if (sets.length === 0) return this.getById(alertId);

    const sql = `UPDATE alerts SET ${sets.join(', ')}
                 WHERE id = $${idx++} AND version = $${idx++}
                 RETURNING *`;
    params.push(alertId, input.version);

    const res = await this.pool.query<Alert>(sql, params);
    if (res.rowCount === 0) {
      const existing = await this.getById(alertId);
      if (!existing) return null; // 404
      throw Object.assign(new Error('Version mismatch'), { code: 'CONFLICT', status: 409 });
    }
    return res.rows[0];
  }

  // ---------- status transitions ----------

  private async validateStatusTransition(
    alertId: number,
    newStatus: AlertStatus,
  ): Promise<void> {
    const validTransitions: Record<AlertStatus, AlertStatus[]> = {
      active:    ['paused', 'triggered', 'expired'],
      paused:    ['active', 'expired'],
      triggered: ['active', 'expired'],
      expired:   [], // terminal
    };

    const current = await this.getById(alertId);
    if (!current) return; // let the caller handle 404
    if (!validTransitions[current.status]?.includes(newStatus)) {
      throw Object.assign(
        new Error(`Cannot transition from ${current.status} to ${newStatus}`),
        { code: 'INVALID_TRANSITION', status: 400 },
      );
    }
  }

  // ---------- delete (cascade) ----------

  async delete(alertId: number): Promise<boolean> {
    const client: PoolClient = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query('DELETE FROM alert_conditions WHERE alert_id = $1', [alertId]);
      await client.query('DELETE FROM alert_history WHERE alert_id = $1', [alertId]);
      const res = await client.query('DELETE FROM alerts WHERE id = $1', [alertId]);
      await client.query('COMMIT');
      return (res.rowCount ?? 0) > 0;
    } catch (e) {
      await client.query('ROLLBACK');
      throw e;
    } finally {
      client.release();
    }
  }

  // ---------- validation ----------

  private validateCreate(input: CreateAlertInput): void {
    if (!input.symbol || !/^[A-Z0-9/-]{2,20}$/i.test(input.symbol)) {
      throw Object.assign(new Error('Invalid symbol format'), { code: 'VALIDATION_ERROR', status: 400 });
    }
    if (input.threshold <= 0) {
      throw Object.assign(new Error('Threshold must be > 0'), { code: 'VALIDATION_ERROR', status: 400 });
    }
    if (!input.channels || input.channels.length === 0) {
      throw Object.assign(new Error('At least one channel required'), { code: 'VALIDATION_ERROR', status: 400 });
    }
  }
}

// ---------- event publisher interface (injected) ----------

export interface AlertEventPublisher {
  publishAlertStateChanged(event: {
    alert_id: number;
    user_id: string;
    old_status: AlertStatus | null;
    new_status: AlertStatus;
    timestamp: Date;
  }): Promise<void>;
}
