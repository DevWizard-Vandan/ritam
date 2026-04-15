path = 'src/learning/intraday_resolver.py'
with open(path, 'r') as f:
    src = f.read()

old_query = '''            SELECT id, timestamp, predicted_direction
            FROM predictions
            WHERE (id NOT IN (SELECT prediction_id FROM prediction_errors)
               OR id IN (SELECT prediction_id FROM prediction_errors WHERE direction_correct IS NULL))
              AND source = 'intraday'
              AND timestamp <= ?'''

new_query = '''            SELECT id, timestamp, predicted_direction
            FROM predictions
            WHERE resolved = 0
              AND source = 'intraday'
              AND timestamp <= ?'''

old_increment = '            resolved_count += 1'
new_increment = '''            conn.execute(
                "UPDATE predictions SET resolved = 1, signal = ? WHERE id = ?",
                (signal_str, pred_id)
            )
            resolved_count += 1'''

src = src.replace(old_query, new_query)
src = src.replace(old_increment, new_increment, 1)

with open(path, 'w') as f:
    f.write(src)
print('Patched!')