"""
Resolves outcomes for predictions made on 15-min intraday candles.
A prediction is resolved when 5 candles (75 minutes) have closed
after the prediction candle.
"""
from loguru import logger
from src.data.db import get_connection, read_intraday_candles
from src.config import settings


def resolve_intraday_outcomes() -> int:
    """
    Finds predictions with source='intraday' that are unresolved,
    looks up the close price 5 candles forward, sets direction,
    and marks as resolved.
    Returns count of resolved predictions.
    """
    from datetime import datetime
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    now_ts = datetime.now(ist).isoformat()

    with get_connection() as conn:
        # Get unresolved intraday predictions
        pending = conn.execute("""
            SELECT id, timestamp, predicted_direction
            FROM predictions
            WHERE resolved = 0
              AND source = 'intraday'
              AND timestamp <= ?
        """, (now_ts,)).fetchall()

        resolved_count = 0
        for pred in pending:
            pred_id, predicted_at, signal_str = pred

            if signal_str == "buy":
                signal = 1
            elif signal_str == "sell":
                signal = -1
            else:
                signal = 0

            # Get all candles after prediction timestamp
            candles_after = conn.execute("""
                SELECT close, timestamp_ist FROM intraday_candles
                WHERE symbol = ?
                  AND timestamp_ist > ?
                ORDER BY timestamp_ist ASC
                LIMIT ?
            """, (settings.INTRADAY_SYMBOL, predicted_at,
                  settings.INTRADAY_OUTCOME_CANDLES)).fetchall()

            if len(candles_after) < settings.INTRADAY_OUTCOME_CANDLES:
                # Not enough candles yet — skip
                continue

            # Close at prediction time
            entry_close = conn.execute("""
                SELECT close FROM intraday_candles
                WHERE symbol = ? AND timestamp_ist <= ?
                ORDER BY timestamp_ist DESC LIMIT 1
            """, (settings.INTRADAY_SYMBOL, predicted_at)).fetchone()

            if not entry_close:
                continue

            entry_price = entry_close[0]
            exit_price = candles_after[-1][0]   # close of 5th candle
            actual_return = (exit_price - entry_price) / entry_price * 100

            # Determine outcome vs signal
            if signal == 1:
                correct = 1 if actual_return > 0.05 else 0
            elif signal == -1:
                correct = 1 if actual_return < -0.05 else 0
            else:
                correct = 1 if abs(actual_return) < 0.3 else 0

            actual_dir = "buy" if actual_return > 0 else "sell" if actual_return < 0 else "hold"

            # Check if prediction_errors entry exists
            existing_err = conn.execute("SELECT id FROM prediction_errors WHERE prediction_id = ?", (pred_id,)).fetchone()

            if existing_err:
                conn.execute("""
                    UPDATE prediction_errors SET
                        actual_direction = ?,
                        actual_move_pct = ?,
                        direction_correct = ?,
                        magnitude_error = 0,
                        scored_at = ?
                    WHERE prediction_id = ?
                """, (actual_dir, round(actual_return, 4), correct, now_ts, pred_id))
            else:
                conn.execute("""
                    INSERT INTO prediction_errors (prediction_id, actual_direction, actual_move_pct, direction_correct, magnitude_error, scored_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pred_id, actual_dir, round(actual_return, 4), correct, 0.0, now_ts))

            # Also update the feedback tracker if using sqlite db
            # Need to update feedback_predictions directly since there's a conflict in schema structure across files
            # Feedback tracker uses a separate table called feedback_predictions and marks resolved = 1
            try:
                conn.execute("""
                    UPDATE feedback_predictions
                    SET actual_return_pct = ?, resolved = 1
                    WHERE timestamp = ?
                """, (round(actual_return, 4), predicted_at))
            except Exception:
                pass # ignore if feedback_predictions not used

            conn.execute(
                    "UPDATE predictions SET resolved = 1, predicted_direction = ? WHERE id = ?",
                (signal_str, pred_id)
            )
            resolved_count += 1

        conn.commit()

    if resolved_count:
        logger.info(f"Resolved {resolved_count} intraday predictions")
    return resolved_count
