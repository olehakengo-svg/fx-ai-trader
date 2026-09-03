"""行鮮度・エンジン生存の判定ポリシー (SSOT).

rule:R3 (2026-08-29). ここは **閾値と時計の定義を 1 箇所に集約する**ための
モジュールである。判定そのもの (通知するか) は ``scripts/anomaly_watcher.py``
の検知器が持ち、本モジュールはその検知器と**同じ定数・同じ時計**で
「いま画面に何と出すか」を決める。

なぜ分離したか — 2026-08-21〜08-25 の Disk 満杯事故では全 SQLite 書込みが
3.5 日停止したが、**ダッシュボードには何の異常も出なかった**。凍結した画面
は「静かな相場」と見分けがつかない。alert 経路は PR #205/#206、status
payload は PR #207/#208 で塞いだが、**人間が実際に見る画面**は最後まで
blind のままだった。

その画面表示を作るとき、閾値 (15分 / 6h / 24h) と週末除外ロジックを
JavaScript 側に書き写すのが最も安直な実装だが、それは本プロジェクトが
繰り返し踏んできた罠そのものである:

- PR #168: ``ctx.hour_utc`` の call-site 欠落で live が 123 日間定数固着
- PR #204: ``bar_time`` の call-site 欠落で全行 NULL
- PR #199: 設定リストにコメントを足したら guard の regex が黙って打ち切られ、
  **全テスト green のまま**検査が無力化した

いずれも「同じ事実を 2 箇所に書き、片方だけ更新された」型である。閾値を
Python と JS の 2 箇所に持てば、``ENGINE_TICK_STALL_MINUTES`` を上げたとき
画面だけ古い閾値で色を塗り続ける — しかも**全テストは green のまま**。
したがって判定はサーバ側で完結させ、ブラウザには**判定済みの結果だけ**を
渡す。JS は色を塗るだけで、閾値を知らない。

時計の使い分け (混同するとどちらかが必ず誤る):

==========================  ==========================  ==================
系列                         時計                         閾値
==========================  ==========================  ==================
``engine_tick``             **実時間 (wall clock)**       15 分
``candidate_row``           市場オープン時間               6 時間
``trade_row``               市場オープン時間               24 時間
``live_fill_row``           市場オープン時間               120 時間
==========================  ==========================  ==================

tick は市場が閉まっていても前進する (``_tick`` が週末に early-return する
のは *戻ってから*カウントされるため) ので、ここで週末を除外すると**本物の
週末停止を毎週見逃す**。逆に候補行・約定行は市場が閉まれば当然止まるので、
実時間で数えると毎週末必ず誤発火する。

⚠️ **``trade_row`` は「約定」の系列ではない** (2026-09-03 訂正、rule:R3)。
``demo_trades`` は shadow 行と LIVE 行を同居させており、実測で
**501 行中 LIVE は 1 行 = 99.8% が shadow**。したがって ``trade_row`` が
測っているのは「``demo_trades`` に何か書けたか」= 書込み経路の生死であって、
**実弾が約定したかではない**。両者は 2026-08-26〜09-03 に実際に乖離した:
LIVE 約定は 133 市場オープン時間ゼロだったのに ``trade_row`` は常時
数分以内で ``ok`` を返し続けた。約定の estimand は ``live_fill_row``
(本モジュールで新設) だけが答えられる。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# ── 閾値 (SSOT) ───────────────────────────────────────────────────────────
# 実測根拠は scripts/anomaly_watcher.py の各 check_* docstring を参照。
# 値を動かすときは *ここだけ* を動かす — watcher も画面も本モジュールを見る。
N_STAGNATION_HOURS = 24
CANDIDATE_STAGNATION_HOURS = 6
ENGINE_TICK_STALL_MINUTES = 15
FX_WEEKEND_CLOSE_HOURS = 48  # 金 21:00 UTC → 日 21:00 UTC

# LIVE 約定 (oanda_trade_id 有り) の停止閾値。市場オープン時間で数える。
#
# 実測較正 (2026-09-03、本番 /api/demo/trades 6,000 行 = 2026-06-24〜09-03、
# LIVE 約定 63 件 / 到着間隔 62 本):
#
#   全期間      median  5.0h / p90 43.2h / max 224.7h
#   carve-out 後 (2026-07-29〜, n=15)  median 30.0h / p90 65.8h / **max 75.3h**
#
# 全期間の max 224.7h は 2026-07-15→07-29 のギャップで、``_is_xau_inst``
# バグが preserve 型 LIVE 送信を 3.5 ヶ月殺していた時期の末端である
# (PR #119→#124 で修復、修復直後の 07-29 04:44 が次の約定)。**現行構成には
# 存在しない母集団**なので閾値較正から除外する — 逆に「その 224.7h を含めて
# max の n 倍」と決めると、消滅済みバグの尾で閾値が膨らみ本物のドリフトを
# 見逃す (2026-09-01 の候補行較正で踏んだ「max の 3 倍」の鏡像)。
#
# 120h = carve-out 後 max の 1.59 倍。閾値 replay の結果:
#   thr=72h  → carve-out 後に 1 回誤発火   (不採用)
#   thr=96h  → 誤発火 0 だが max の 1.27 倍しか余裕が無い (n=15 では薄い)
#   **thr=120h → 誤発火 0 / 全期間では 1 回だけ発火 = 上記 preserve バグの
#     尾 (= 真陽性)。すなわち本検知器が当時あればあのバグを捕捉できた**
#   thr=144h → 2026-09-03 の実ドリフト (133.3h) を取り逃す (不採用)
#
# ⚠️ n=15 は薄い。誤発火が出たら**上げる** (下げるのは実測を取り直してから)。
LIVE_FILL_STAGNATION_HOURS = 120


def market_open_hours(start: datetime, end: datetime) -> float:
    """[start, end] の実時間から FX 週末閉場 (金 21:00 → 日 21:00 UTC) を除く.

    閉場境界は夏時間で 21:00/22:00 と揺れるが、24h 閾値に対する ±1h の
    誤差は無害なので UTC 21:00 固定とする。
    """
    if end <= start:
        return 0.0
    total = (end - start).total_seconds() / 3600.0
    closed = 0.0
    # start 以前で最も近い金曜 21:00 UTC に錨を置き、週単位で閉場窓を歩く
    anchor = (start - timedelta(days=(start.weekday() - 4) % 7)).replace(
        hour=21, minute=0, second=0, microsecond=0
    )
    if anchor > start:
        anchor -= timedelta(days=7)
    while anchor < end:
        overlap = (
            min(end, anchor + timedelta(hours=FX_WEEKEND_CLOSE_HOURS)) - max(start, anchor)
        ).total_seconds() / 3600.0
        if overlap > 0:
            closed += overlap
        anchor += timedelta(days=7)
    return total - closed


# ── UI 判定 ───────────────────────────────────────────────────────────────
# level の意味 (画面の色と 1:1):
#   ok      … 閾値内。正常
#   stale   … 閾値超過。watcher が同じ入力で alert を上げる状態
#   idle    … 「止められている」/ まだ 1 行も無い。異常ではない
#             (資格 eligible と実状態 effective の区別 — 全モード停止中の
#              エンジンは「止まっている」のではなく「止められている」)
#   unknown … 値が無い / 壊れている。**沈黙させない** — 126 日 no-op の
#             原因は「無ければ skip」だった
LEVEL_OK = "ok"
LEVEL_STALE = "stale"
LEVEL_IDLE = "idle"
LEVEL_UNKNOWN = "unknown"

_LEVEL_RANK = {LEVEL_OK: 0, LEVEL_IDLE: 1, LEVEL_UNKNOWN: 2, LEVEL_STALE: 3}


def _fmt_age(seconds: float | None) -> str:
    """経過秒を人間可読に (画面幅が狭いので単位は 1 つだけ)."""
    if seconds is None:
        return "—"
    s = float(seconds)
    if s < 90:
        return f"{s:.0f}秒"
    if s < 5400:
        return f"{s / 60:.0f}分"
    if s < 172800:
        return f"{s / 3600:.1f}時間"
    return f"{s / 86400:.1f}日"


def _parse_ts(raw: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _engine_family(status: dict[str, Any]) -> dict[str, Any]:
    """エンジン tick — **発火 = エンジン異常**と読んでよい唯一の系列.

    週末除外は意図的にしない (モジュール docstring 参照)。
    """
    out: dict[str, Any] = {
        "key": "engine_tick",
        "label": "エンジン",
        "clock": "wall",
        "threshold_text": f"{ENGINE_TICK_STALL_MINUTES}分",
    }
    st = status.get("engine_tick_status")
    if st is None:
        out.update(level=LEVEL_UNKNOWN, age_text="—", detail="status に engine_tick_* 無し (版ずれ?)")
        return out
    if st == "not_running":
        out.update(level=LEVEL_IDLE, age_text="—", detail="全モード停止中")
        return out

    age = status.get("engine_tick_age_sec")
    try:
        age_sec = float(age)
    except (TypeError, ValueError):
        # never_ticked かつ経過秒不明 = 起動失敗の疑い (最悪ケース)。
        # 版ずれと同じ袋に入れると沈黙するので stale 側に倒す。
        if st == "never_ticked":
            out.update(level=LEVEL_STALE, age_text="—", detail="tick ゼロ・経過秒不明 (起動失敗の疑い)")
        else:
            out.update(level=LEVEL_UNKNOWN, age_text="—", detail=f"engine_tick_age_sec 不正 ({age!r})")
        return out

    modes = status.get("engine_tick_running_modes")
    stalest_mode = status.get("engine_tick_stalest_mode")
    stalest_age = status.get("engine_tick_stalest_age_sec")
    detail_parts = []
    if modes is not None:
        detail_parts.append(f"{modes} モード稼働")
    if stalest_mode:
        detail_parts.append(f"最遅 {stalest_mode} {_fmt_age(stalest_age)}")

    out.update(
        age_sec=round(age_sec, 1),
        age_text=_fmt_age(age_sec),
        detail=" / ".join(detail_parts) or "—",
    )
    if age_sec >= ENGINE_TICK_STALL_MINUTES * 60:
        out["level"] = LEVEL_STALE
        if st == "never_ticked":
            out["detail"] = "起動から tick ゼロ" + (f" / {out['detail']}" if detail_parts else "")
    elif st == "never_ticked":
        # 起動直後の ramp 中 (PR #199 実測で 3.6 分)。まだ異常ではない。
        out["level"] = LEVEL_IDLE
        out["detail"] = "起動直後 (tick 待ち)"
    else:
        out["level"] = LEVEL_OK
    return out


def _row_family(
    status: dict[str, Any],
    now: datetime,
    *,
    key: str,
    label: str,
    threshold_hours: float,
) -> dict[str, Any]:
    """候補行 / トレード行 / LIVE 約定 — 市場オープン時間で数える系列.

    ⚠️ estimand: ``candidate_row`` は v9.1 HTF Hard Block の **後**に書かれる。
    「エンジンが評価しているか」ではなく「候補が select_best に到達したか」で
    あり、発火しても engine 停止と断定してはならない (2026-08-27 の 73 分
    ゼロ行は全候補 HTF ブロックが実体で、tick は前進していた)。
    エンジン生存は上の ``engine_tick`` 行だけが答えられる。

    ⚠️ estimand: ``trade_row`` は shadow 込みの ``demo_trades`` 全体、
    ``live_fill_row`` は ``oanda_trade_id`` を持つ行だけ。**3 系列とも別物**で、
    「候補は出ている / 行は書けている / だが実弾は出ていない」を分離するのが
    本ファミリの目的である。畳むと 2026-08-26〜09-03 の 133 市場オープン時間
    LIVE ゼロが「正常」に見える (実際そう見えていた)。
    """
    out: dict[str, Any] = {
        "key": key,
        "label": label,
        "clock": "market_open",
        "threshold_text": f"{threshold_hours:g}時間",
    }
    st = status.get(f"last_{key}_status")
    if st is None:
        out.update(level=LEVEL_UNKNOWN, age_text="—", detail=f"status に last_{key}_* 無し (版ずれ?)")
        return out
    if st == "error":
        out.update(
            level=LEVEL_UNKNOWN,
            age_text="—",
            detail=str(status.get("row_freshness_error") or "鮮度クエリ失敗")[:120],
        )
        return out
    if st != "ok":
        # no_table / no_rows は初期状態。異常ではないが「ok」でもない。
        out.update(level=LEVEL_IDLE, age_text="—", detail=f"行なし ({st})")
        return out

    raw_at = status.get(f"last_{key}_at")
    latest = _parse_ts(raw_at)
    if latest is None:
        out.update(level=LEVEL_UNKNOWN, age_text="—", detail=f"時刻が読めない ({raw_at!r})")
        return out

    open_h = market_open_hours(latest, now)
    wall_sec = (now - latest).total_seconds()
    out.update(
        age_sec=round(wall_sec, 1),
        age_text=_fmt_age(wall_sec),
        market_open_hours=round(open_h, 1),
        last_at=str(raw_at),
        level=LEVEL_STALE if open_h >= threshold_hours else LEVEL_OK,
    )
    # 実時間が閾値を超えていても市場オープン換算では超えない = 週末。
    # 画面に「なぜ古くて正常なのか」を書かないと、次の人が誤読する。
    if out["level"] == LEVEL_OK and wall_sec / 3600.0 >= threshold_hours:
        out["detail"] = f"市場オープン換算 {open_h:.1f}h (閉場ぶんを除外)"
    else:
        out["detail"] = f"市場オープン換算 {open_h:.1f}h"
    return out


def classify_freshness(
    status: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """status payload から画面用の鮮度判定を作る.

    ブラウザに閾値を渡さないため、**判定済みの level と表示文字列だけ**を
    返す。JS は色を塗るだけで、15 分 / 6h / 24h を知らない。
    """
    now = now or datetime.now(timezone.utc)
    status = status or {}
    families = [
        _engine_family(status),
        _row_family(
            status, now,
            key="candidate_row", label="候補行",
            threshold_hours=CANDIDATE_STAGNATION_HOURS,
        ),
        # ⚠️ ラベルは「約定行」ではない — この系列は shadow 行を含む
        # demo_trades 全体の書込み鮮度である (モジュール docstring 参照)。
        # 画面に「約定」と書くと、shadow だけが流れている状態を「実弾が
        # 出ている」と誤読させる。実際 2026-08-26〜09-03 はそう見えていた。
        _row_family(
            status, now,
            key="trade_row", label="トレード行 (shadow込)",
            threshold_hours=N_STAGNATION_HOURS,
        ),
        _row_family(
            status, now,
            key="live_fill_row", label="LIVE 約定",
            threshold_hours=LIVE_FILL_STAGNATION_HOURS,
        ),
    ]
    worst = max(families, key=lambda f: _LEVEL_RANK.get(f.get("level"), 0))
    return {
        "families": families,
        "worst_level": worst.get("level", LEVEL_UNKNOWN),
        "generated_at": now.isoformat(),
    }
