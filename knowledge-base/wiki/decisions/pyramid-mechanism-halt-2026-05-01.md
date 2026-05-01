# PYR (Risk-Free Pyramiding) 機構の Live 一時停止 — 2026-05-01

**Decision rule**: R2 (Fast & Reactive — 損失停止)
**Status**: HALTED via env-var gate (default `PYRAMID_ENABLED=0`)
**Affected code**: `modules/demo_trader.py:1855-1917`

## 背景

`fx-ai-trader` の v6.4 から導入された **Risk-Free Pyramiding** は、Live (OANDA) ポジションが 1.0 ATR 有利方向に動いた段階で:

1. 親の SL を建値 (BE) へ引き上げ
2. 同方向に +10,000u を **SL = 親オリジナル建値** で追加発注
3. TP は親と共通

「最悪 BE / 最良で追加分の利益増幅」を意図した設計だったが、Live 実測で構造的に負けていることが判明。

## Audit 結果（[pyr-mechanism-live-audit-2026-05-01.md](../analyses/pyr-mechanism-live-audit-2026-05-01.md)）

**期間**: 2026-04-09 → 2026-04-30 (約 3 週間)
**N**: 23 (7 親戦略にまたがる)

| 指標 | 値 | 解釈 |
|---|---|---|
| Decided WR | **5.9%** (TP 1 / SL 16) | 50% 帰無を圧倒的に下回る |
| Wilson_BF lower (Z=3.29) | **0.005** | 99.9% 信頼下限が 0.5% — 偶然では説明不能 |
| EV per PYR | **-1.56 pip** | 1 件あたり確定的に赤字 |
| 累計 | **-35.9 pip / -5,563 JPY** | 3 週間で 5.5k 円毀損 |
| 保有時間 | **65.2% が ≤5 秒、100% が ≤60 秒** | 構造的に即 SL — 設計失敗のシグナル |

親戦略別では N<10 で個別 Bonferroni 有意ではないが、機構そのものの aggregate 評価としては決定的。

## 根本原因（仮説）

1. **BE-SL 距離が tick ノイズに対して小さすぎる**: 1.0 ATR 進行後に +10,000u をフルロットで建値 SL に投入すると、価格は再び親の建値方向に戻りやすく、わずかな逆行・スプレッド広がりで即発火
2. **トリガー条件 "1.0 ATR 移動" が早すぎる**: 反転確率の高い領域で乗せている可能性
3. **ルートが親側に偏る**: 7 親中 vol_momentum_scalp が 8 件、orb_trap が 6 件 — 特定 mode が disproportionately ヒット → mode 別の挙動差検証が必要

## 採用した処置 (rule:R2)

`modules/demo_trader.py:1864` に env-var ゲートを追加:

```python
_PYRAMID_ENABLED = _os.environ.get("PYRAMID_ENABLED", "0") == "1"
if (_PYRAMID_ENABLED
        and trade_id not in self._pyramided_trades
        and _has_oanda_id
        and _entry_type_pe in self._PE_50PCT_ELIGIBLE):
    ...
```

- **Default OFF** (本番でも明示的に `PYRAMID_ENABLED=1` を設定しない限り機構は無効)
- 親戦略の SL→BE 自動引き上げロジックは PYR ブロック内側にあるため、停止時は **SL 引き上げ自体も発火しない** — 親の挙動は v6.4 以前と同等
- `_pyramided_trades` set への登録は無いため、再有効化時に過去の親が一律対象から外れることはない

## 影響範囲の最小化

- 親戦略 (gbp_deep_pullback / xs_momentum / vol_momentum_scalp / orb_trap / session_time_bias / trendline_sweep / vix_carry_unwind) の本来エッジには触れない
- shadow / sentinel routes は PYR を呼ばないため影響なし
- 表示側 ([modules/demo_db.py:1618, 1665](../../modules/demo_db.py)) は PYR_ 親解決を残す — 過去ログの可視性を保つ

## 再有効化条件（Pre-registered）

以下を満たすまで `PYRAMID_ENABLED=1` には戻さない:

1. **設計改修**: SL 距離を BE 固定ではなく、エントリー時 ATR の N% (例: 0.3 ATR) や直近 swing low/high 等に変更
2. **Shadow バックテスト**: 改修案を `_bt_*.py` で 365 日 BT し、EV ≥ 0 かつ Wilson_BF 下限 > 0.50 を確認
3. **Shadow Live N≥30**: 実環境で SHADOW_MODE のみで動かし、N≥30 で WR > 50% を Bonferroni 有意で確認
4. **Pre-registration**: 上記 1-3 を `wiki/research/` か `wiki/strategies/` に LOCK 文書化してから再有効化

## 想定外シナリオ

- **再有効化したが直る保証は無い**: 親戦略の選定 (`_PE_50PCT_ELIGIBLE`) と TP 位置の関数として PYR の運命が決まるため、母集団の入れ替えで EV が変わる可能性。Shadow N≥30 が最低条件
- **逆効果が現れる場合**: PYR 停止後に親戦略の TP 到達率が下がる場合は、PYR の SL→BE 引き上げが副次的に親の早期撤退も封じていた可能性 → その場合は SL→BE のみを残し PYR 注文を切るバリアント (Track C) を別途検討

## 関連変更

- 表示バグ修正 ([demo_db.py:1618, 1665](../../modules/demo_db.py)): PYR_ 子の strategy 列が空欄になる問題を解消し、過去 PYR の親戦略を `<parent> (PYR)` 形式で可視化
- audit カラム二義性メモ: `oanda_audit.entry_type` は `bridge_status='sent'` で戦略名、`'filled'` で MODE 名 — `wiki/lessons/` 系の集計クエリで GROUP BY する前に分離が必須
