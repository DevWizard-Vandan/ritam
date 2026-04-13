/* ── API Types ── */

export interface Candle {
  timestamp_ist: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface CandlesResponse {
  symbol: string;
  candles: Candle[];
}

export interface SignalByType {
  total: number;
  correct: number;
  accuracy_pct: number;
}

export interface AccuracyResponse {
  total: number;
  correct: number;
  accuracy_pct: number;
  avg_error: number;
  by_signal: {
    buy: SignalByType;
    sell: SignalByType;
    hold: SignalByType;
  };
}

export interface Analog {
  start_date: string;
  end_date: string;
  similarity_score: number;
  next_5day_return: number;
}

export interface ExplanationResponse {
  explanation: string;
  timestamp: string;
}

export interface PredictionData {
  timestamp: string;
  predicted_direction: string;
  predicted_move_pct: number;
  confidence: number;
  timeframe_minutes: number;
  regime: string;
}

export interface WsPredictionMessage {
  type: 'prediction';
  data: PredictionData;
}
