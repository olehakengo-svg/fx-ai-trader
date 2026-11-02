# Daily Observations — 2026-11 (S0 intake 層、記述級のみ)

**Protocol**: [[daily-market-review-protocol]] — p 値計算禁止 / α 消費ゼロ / 台帳番号なし / 卒業には ban/estimand 監査必須 / 凍結 look 保有 family の outcome 量は記載禁止 (registry 事前確認)。前月: [[daily-observations-2026-10]]

---

### O-2026-11-02-1: グローバル建玉上限 `max_open`=8 が shadow 建玉を数え、carry_dip の live-eligible シグナルを shadow 化 (Live vs Shadow 分離の違反、live 機会喪失 1/12) (執行 QA / 制御系)
- **現象**: 2026-10-30 08:02:59Z `usdjpy_carry_dip_accumulator` BUY USD_JPY (demo row 20285、confluence STRONG、`[SLTP_CONSTRUCT] sl_p=18.6 tp_p=80.3`) が `[SHADOW_BYPASS] max_open` で `is_shadow=1` として記録。oanda_audit 同時刻行は `bridge_status=skipped / block_reason=shadow_tracking / is_live=false`。同時刻の open live 建玉は 0 (kalman #1346985 は 10-29 20:01Z 決済済み、carry_dip 21:04Z は `MARKET_HALTED`) = 上限 8 を埋めていたのは **shadow 建玉のみ**
- **トリガ日**: 2026-10-30 (観測 2026-11-02、autopilot run)
- **想定メカニズム**: `modules/demo_trader.py` の max_open 節は `_n_open = len(open_trades)` (live + shadow の総数) を live 上限 `max_open_trades`=8 と比較し、`_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` 非所属の live-eligible 型は `_is_slot_shadow_eligible` 経由で shadow に落とす (shadow 側の上限は max_open+8)。per-cell 上限 (`max_per_mode_pair`) は 2026-04-30 に live / shadow を別カウント化済みだが、グローバル上限は未分離。kalman_d7 3 variant は bypass 所属のため影響 0、carry_dip は非所属
- **規模**: 単一エンジン期 (10-05〜11-02、PROD snapshot 20,307 行) の live-eligible 型 `[SHADOW_BYPASS] max_open` = carry_dip **1 件** / live-eligible 発火 12 件 (LIVE 11 + max_open 1; 別に `MARKET_HALTED` 由来の shadow 化 2 件は別機構)。全型では 9 件
- **経路**: rule:R3 構造バグ (shadow が live を削る = 原則 1 + [[feedback_live_vs_shadow_strict_separation]])。修理 = live cap を `is_shadow` 偽の建玉数で判定 (shadow cap は総数のまま)。live 経路変更のため review gate + open live 0 の窓でマージ。registry `max-open-live-cap-counts-shadow-r3` (11-04)。lot / シグナル / 凍結値は非接触。outcome は読まない
