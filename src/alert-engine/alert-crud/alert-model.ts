// Alert CRUD — core data types

export type ConditionType =
  | 'price_above' | 'price_below' | 'price_crosses'
  | 'rsi_above' | 'rsi_below'
  | 'macd_cross' | 'macd_divergence'
  | 'sma_cross' | 'ema_cross'
  | 'bollinger_break' | 'stoch_k_cross'
  | 'atr_break' | 'ichimoku_break'
  | 'volume_profile' | 'fibonacci_retrace'
  | 'head_shoulders' | 'double_top' | 'double_bottom'
  | 'triangle_break' | 'wedge_break' | 'flag_pattern';

export type AlertStatus = 'active' | 'paused' | 'triggered' | 'expired';

export type ChannelType = 'push' | 'email' | 'sms';

export interface Alert {
  id: number;
  user_id: string;
  symbol: string;
  condition_type: ConditionType;
  threshold: number;
  channels: ChannelType[];
  status: AlertStatus;
  version: number;
  created_at: Date;
  updated_at: Date;
}

export interface AlertCondition {
  id: number;
  alert_id: number;
  condition_type: ConditionType;
  params: Record<string, unknown>;
  created_at: Date;
}

export interface AlertHistory {
  id: number;
  alert_id: number;
  triggered_at: Date;
  price: number;
  notification_status: 'pending' | 'delivered' | 'failed';
  created_at: Date;
}

export interface CreateAlertInput {
  user_id: string;
  symbol: string;
  condition_type: ConditionType;
  threshold: number;
  channels: ChannelType[];
}

export interface UpdateAlertInput {
  symbol?: string;
  condition_type?: ConditionType;
  threshold?: number;
  channels?: ChannelType[];
  status?: AlertStatus;
  version: number;
}

export interface AlertListFilter {
  user_id?: string;
  status?: AlertStatus;
  page?: number;
  limit?: number;
}

export const ALERT_FREE_LIMIT = 5;

const FREE_TYPES: Set<ConditionType> = new Set([
  'price_above', 'price_below', 'price_crosses',
]);

const PREMIUM_ONLY_TYPES: ConditionType[] = [
  'rsi_above', 'rsi_below', 'macd_cross', 'macd_divergence',
  'sma_cross', 'ema_cross', 'bollinger_break', 'stoch_k_cross',
  'atr_break', 'ichimoku_break', 'volume_profile', 'fibonacci_retrace',
  'head_shoulders', 'double_top', 'double_bottom',
  'triangle_break', 'wedge_break', 'flag_pattern',
];

export function isTypeRestricted(
  conditionType: ConditionType,
  tier: 'free' | 'premium',
): boolean {
  if (tier === 'premium') return false;
  return !FREE_TYPES.has(conditionType);
}

export function premiumOnlyTypes(): ReadonlyArray<ConditionType> {
  return PREMIUM_ONLY_TYPES;
}
