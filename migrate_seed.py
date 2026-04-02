"""
Render Disk migration seed script.
Inserts pre-existing trades into the new persistent DB on first deploy.
Run automatically at startup if DB is empty.
"""
import sqlite3, json, os

SEED_TRADES = [
    # === CLOSED trades (18) ===
    {"trade_id":"304a1909-2ef","status":"CLOSED","direction":"BUY","entry_price":159.547,"entry_time":"2026-04-02T08:17:17.329000+00:00","exit_price":159.732,"exit_time":"2026-04-02T11:14:04.418320+00:00","sl":159.45,"tp":159.721,"pnl_pips":18.5,"pnl_r":1.91,"outcome":"WIN","entry_type":"ema_cross","confidence":70,"tf":"15m","mode":"daytrade","close_reason":"TP_HIT","ema_conf":95,"sr_basis":159.477,"layer1_dir":"bull","score":3.0,"reasons":json.dumps(["EMA cross BUY","ADX41","EMA200 above"]),"regime":"{}","created_at":"2026-04-02 08:17:17"},
    {"trade_id":"e70e193d-083","status":"CLOSED","direction":"BUY","entry_price":159.567,"entry_time":"2026-04-02T08:18:04.028405+00:00","exit_price":159.615,"exit_time":"2026-04-02T08:22:03.845542+00:00","sl":159.536,"tp":159.614,"pnl_pips":4.8,"pnl_r":1.55,"outcome":"WIN","entry_type":"bb_rsi_reversion","confidence":61,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":61,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:18:04"},
    {"trade_id":"e4f10e20-c63","status":"CLOSED","direction":"SELL","entry_price":159.567,"entry_time":"2026-04-02T08:18:20.478488+00:00","exit_price":159.657,"exit_time":"2026-04-02T08:49:03.678848+00:00","sl":160.047,"tp":158.847,"pnl_pips":-9.0,"pnl_r":-0.19,"outcome":"LOSS","entry_type":"h1_fib_reversal","confidence":36,"tf":"1h","mode":"daytrade_1h","close_reason":"SIGNAL_REVERSE","ema_conf":36,"sr_basis":0.0,"layer1_dir":"neutral","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:18:20"},
    {"trade_id":"79a06523-b6d","status":"CLOSED","direction":"BUY","entry_price":159.652,"entry_time":"2026-04-02T08:34:48.519288+00:00","exit_price":159.548,"exit_time":"2026-04-02T10:02:05.170360+00:00","sl":159.549,"tp":159.838,"pnl_pips":-10.4,"pnl_r":-1.01,"outcome":"LOSS","entry_type":"ema_cross","confidence":73,"tf":"15m","mode":"daytrade","close_reason":"SL_HIT","ema_conf":95,"sr_basis":159.477,"layer1_dir":"bull","score":3.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:34:48"},
    {"trade_id":"63a37527-bad","status":"CLOSED","direction":"SELL","entry_price":159.672,"entry_time":"2026-04-02T08:38:06.552030+00:00","exit_price":159.63,"exit_time":"2026-04-02T08:50:06.857316+00:00","sl":159.702,"tp":159.634,"pnl_pips":4.2,"pnl_r":1.4,"outcome":"WIN","entry_type":"bb_rsi_reversion","confidence":39,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":39,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:38:06"},
    {"trade_id":"10199ca9-f62","status":"CLOSED","direction":"BUY","entry_price":159.629,"entry_time":"2026-04-02T08:51:12.560486+00:00","exit_price":159.681,"exit_time":"2026-04-02T08:57:07.300316+00:00","sl":159.596,"tp":159.679,"pnl_pips":5.2,"pnl_r":1.58,"outcome":"WIN","entry_type":"fib_reversal","confidence":65,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":65,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:51:12"},
    {"trade_id":"6d46d02b-c4d","status":"CLOSED","direction":"SELL","entry_price":159.682,"entry_time":"2026-04-02T08:59:04.529700+00:00","exit_price":159.72,"exit_time":"2026-04-02T09:13:04.924186+00:00","sl":159.712,"tp":159.643,"pnl_pips":-3.8,"pnl_r":-1.27,"outcome":"LOSS","entry_type":"bb_rsi_reversion","confidence":37,"tf":"1m","mode":"scalp","close_reason":"SL_HIT","ema_conf":37,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 08:59:04"},
    {"trade_id":"4f612280-780","status":"CLOSED","direction":"SELL","entry_price":159.675,"entry_time":"2026-04-02T09:04:30.163400+00:00","exit_price":159.693,"exit_time":"2026-04-02T09:07:04.138796+00:00","sl":160.134,"tp":158.986,"pnl_pips":-1.8,"pnl_r":-0.04,"outcome":"LOSS","entry_type":"h1_fib_reversal","confidence":32,"tf":"1h","mode":"daytrade_1h","close_reason":"SCENARIO_INVALID","ema_conf":32,"sr_basis":0.0,"layer1_dir":"neutral","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:04:30"},
    {"trade_id":"8b0950a4-60b","status":"CLOSED","direction":"BUY","entry_price":159.693,"entry_time":"2026-04-02T09:19:06.733575+00:00","exit_price":159.658,"exit_time":"2026-04-02T09:25:02.739083+00:00","sl":159.663,"tp":159.737,"pnl_pips":-3.5,"pnl_r":-1.17,"outcome":"LOSS","entry_type":"stoch_trend_pullback","confidence":58,"tf":"1m","mode":"scalp","close_reason":"SL_HIT","ema_conf":58,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:19:06"},
    {"trade_id":"5ca7b977-6b5","status":"CLOSED","direction":"BUY","entry_price":159.622,"entry_time":"2026-04-02T09:27:04.134645+00:00","exit_price":159.586,"exit_time":"2026-04-02T09:34:06.678830+00:00","sl":159.589,"tp":159.672,"pnl_pips":-3.6,"pnl_r":-1.09,"outcome":"LOSS","entry_type":"bb_rsi_reversion","confidence":73,"tf":"1m","mode":"scalp","close_reason":"SL_HIT","ema_conf":73,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:27:04"},
    {"trade_id":"dd9204e0-1b0","status":"CLOSED","direction":"SELL","entry_price":159.568,"entry_time":"2026-04-02T09:38:10.348015+00:00","exit_price":159.655,"exit_time":"2026-04-02T10:18:13.374150+00:00","sl":160.045,"tp":158.853,"pnl_pips":-8.7,"pnl_r":-0.18,"outcome":"LOSS","entry_type":"h1_fib_reversal","confidence":36,"tf":"1h","mode":"daytrade_1h","close_reason":"SIGNAL_REVERSE","ema_conf":36,"sr_basis":0.0,"layer1_dir":"neutral","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:38:10"},
    {"trade_id":"4171c55d-579","status":"CLOSED","direction":"BUY","entry_price":159.579,"entry_time":"2026-04-02T09:39:04.195420+00:00","exit_price":159.617,"exit_time":"2026-04-02T09:44:02.849303+00:00","sl":159.549,"tp":159.617,"pnl_pips":3.8,"pnl_r":1.27,"outcome":"WIN","entry_type":"macdh_reversal","confidence":36,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":36,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:39:04"},
    {"trade_id":"6cdf65b1-a80","status":"CLOSED","direction":"SELL","entry_price":159.62,"entry_time":"2026-04-02T09:51:07.195804+00:00","exit_price":159.557,"exit_time":"2026-04-02T10:00:05.307817+00:00","sl":159.656,"tp":159.566,"pnl_pips":6.3,"pnl_r":1.75,"outcome":"WIN","entry_type":"bb_rsi_reversion","confidence":36,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":36,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 09:51:07"},
    {"trade_id":"da7df148-6cd","status":"CLOSED","direction":"BUY","entry_price":159.581,"entry_time":"2026-04-02T10:01:11.630064+00:00","exit_price":159.548,"exit_time":"2026-04-02T10:02:05.150003+00:00","sl":159.551,"tp":159.625,"pnl_pips":-3.3,"pnl_r":-1.1,"outcome":"LOSS","entry_type":"bb_rsi_reversion","confidence":36,"tf":"1m","mode":"scalp","close_reason":"SL_HIT","ema_conf":36,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 10:01:11"},
    {"trade_id":"3e793286-8ae","status":"CLOSED","direction":"BUY","entry_price":159.555,"entry_time":"2026-04-02T10:04:12.393300+00:00","exit_price":159.619,"exit_time":"2026-04-02T10:07:06.533605+00:00","sl":159.525,"tp":159.596,"pnl_pips":6.4,"pnl_r":2.13,"outcome":"WIN","entry_type":"bb_rsi_reversion","confidence":52,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":52,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 10:04:12"},
    {"trade_id":"48a32c4d-3ef","status":"CLOSED","direction":"SELL","entry_price":159.643,"entry_time":"2026-04-02T10:19:04.798643+00:00","exit_price":159.631,"exit_time":"2026-04-02T10:31:03.845348+00:00","sl":159.673,"tp":159.604,"pnl_pips":1.2,"pnl_r":0.4,"outcome":"WIN","entry_type":"mtf_reversal_confluence","confidence":36,"tf":"1m","mode":"scalp","close_reason":"SIGNAL_REVERSE","ema_conf":36,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 10:19:04"},
    {"trade_id":"0cdd1ffa-c5d","status":"CLOSED","direction":"BUY","entry_price":159.631,"entry_time":"2026-04-02T10:31:03.881317+00:00","exit_price":159.672,"exit_time":"2026-04-02T10:51:02.758755+00:00","sl":159.601,"tp":159.672,"pnl_pips":4.1,"pnl_r":1.37,"outcome":"WIN","entry_type":"stoch_trend_pullback","confidence":58,"tf":"1m","mode":"scalp","close_reason":"TP_HIT","ema_conf":58,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 10:31:03"},
    {"trade_id":"4b20ee02-20e","status":"CLOSED","direction":"SELL","entry_price":159.672,"entry_time":"2026-04-02T10:51:05.732566+00:00","exit_price":159.705,"exit_time":"2026-04-02T11:13:03.921123+00:00","sl":159.702,"tp":159.633,"pnl_pips":-3.3,"pnl_r":-1.1,"outcome":"LOSS","entry_type":"bb_rsi_reversion","confidence":38,"tf":"1m","mode":"scalp","close_reason":"SL_HIT","ema_conf":38,"sr_basis":0.0,"layer1_dir":"bull","score":0.0,"reasons":"[]","regime":"{}","created_at":"2026-04-02 10:51:05"},
]

COLUMNS = [
    "trade_id","status","direction","entry_price","entry_time",
    "exit_price","exit_time","sl","tp","pnl_pips","pnl_r","outcome",
    "entry_type","confidence","tf","mode","close_reason","ema_conf",
    "sr_basis","layer1_dir","score","reasons","regime","created_at"
]

def run_seed(db_path: str):
    """Insert seed trades if DB is empty."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    count = conn.execute("SELECT COUNT(*) FROM demo_trades").fetchone()[0]
    if count > 0:
        print(f"[migrate_seed] DB already has {count} trades, skipping seed.")
        conn.close()
        return False

    placeholders = ",".join(["?"] * len(COLUMNS))
    col_names = ",".join(COLUMNS)
    inserted = 0
    for t in SEED_TRADES:
        vals = tuple(t.get(c) for c in COLUMNS)
        try:
            conn.execute(f"INSERT INTO demo_trades ({col_names}) VALUES ({placeholders})", vals)
            inserted += 1
        except Exception as e:
            print(f"[migrate_seed] Skip {t['trade_id']}: {e}")
    conn.commit()
    conn.close()
    print(f"[migrate_seed] Inserted {inserted} seed trades into {db_path}")
    return True


if __name__ == "__main__":
    path = os.environ.get("DB_PATH", "demo_trades.db")
    run_seed(path)
