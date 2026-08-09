# DT ctx.hour_utc が live で 12 に凍結していた構造バグ (2026-08-09)

**Rule**: R3 (構造バグ / 算数破綻 — 365日BT スキップ、code derivation を文書化)
**Status**: ✅ 修正済み (PR: `fix/dt-ctx-hour-utc-live-2026-08-09`)
**発見経路**: `t9-kalman-d7-fire-info` トリガー (実測 0.00/週 vs 期待 3.9/週) の分母調査
**潜伏期間**: 2026-04-08 (`9c849cef` DT構造改革) 〜 2026-08-09 = **123 日**

---

## 1. 結論 (先に)

`compute_daytrade_signal` が組み立てる DaytradeEngine 用 `SignalContext` の
`hour_utc` / `is_friday` が、**live 経路では常に 12 / False に凍結**していた。
BT 経路だけが実バー時刻を受け取っていたため、**DT 全戦略の時間帯ゲートが
BT と live で別物**になっていた。

- **h=12 で閉じる窓を持つ戦略** → live で構造的に発火不能 (shadow N もゼロ)
- **h=12 で開く窓を持つ戦略** → 時間帯ゲートが常時開放、BT 検証窓の外でも live 発火
- **`is_friday` が常に False** → 金曜ブロックが live で一度も作動していない

これは「BT で検証した estimand と live で走っている estimand が違う」型の欠陥であり、
[[bt-live-divergence]] の未計上の主要因の一つ。

---

## 2. Code derivation (一次証拠)

### 2.1 バグ本体

`app.py:2552-2553` (修正前):

```python
_dt_hour_utc = bar_time.hour if bar_time and hasattr(bar_time, 'hour') else 12
_dt_is_friday = bar_time.weekday() == 4 if bar_time and hasattr(bar_time, 'weekday') else False
```

### 2.2 `bar_time` が live で None であること

| 呼び出し元 | 引数 | `bar_time` |
|---|---|---|
| `app.py:6679` (BT ループ) | `bar_time=bar_time` | ✅ 実バー時刻 |
| `app.py:7121` (BT SR 再評価) | `bar_time=_sr_bar_time_dt` | ✅ 実バー時刻 |
| `modules/demo_trader.py:3858` (**live tick**) | `compute_fn(df, tf, sr_for_signal, symbol)` | ❌ **None** |
| `app.py:11288` (API 単発) | `compute_daytrade_signal(df, tf, sr, "USDJPY=X")` | ❌ None |

live は位置引数 4 つのみ → `bar_time=None` → フォールバック 12 が常に採用される。

### 2.3 同一関数内に正しい実装が同居していた

同じ `compute_daytrade_signal` の 4 行上、`is_trade_prohibited` (Layer 0) は
当初から正しいフォールバックを持っていた (`app.py:462`):

```python
now_utc = bar_time if bar_time else datetime.now(timezone.utc)
```

また scalp 経路が使う `SignalContext.from_df` (`strategies/context.py:134-142`) も
`bar_time → row.name → now()` と正しく降りている。**壊れていたのは DT 経路の
直接コンストラクタ呼び出しだけ**という非対称が、発見を 123 日遅らせた。

### 2.4 退行の履歴

`strategies/daytrade/london_session_breakout.py:71` に残るコメント:

> DISABLED: context fix (2026-04-04) で hour_utc が正しく渡されるようになり、初めて実BT可能に

2026-04-04 に一度 hour_utc は修正されている。その 4 日後の `9c849cef`
(2026-04-08, DT構造改革) が `_DtCtx(...)` 直接構築を新設した際に、固定値 12 が
再混入した。**同型バグの再発**。

---

## 3. 本番実測 (二次証拠)

### 3.1 QUALBAR テレメトリ — 直接観測

`[kalman_d7] QUALBAR` 行 (Render app ログ、2026-07-28〜08-07、12 バー) は
**全行が `hour=12`**:

| バー (UTC) | 報告 hour | session_pass |
|---|---|---|
| 07-28 21:15 | 12 | False |
| 07-29 15:45 | 12 | False |
| 08-06 10:30 | 12 | False |
| 08-07 03:00 | 12 | False |
| 08-07 07:15 | 12 | False |
| 08-07 12:15 | 12 | False |
| (他 6 バー) | 12 | False |

実バー時刻は 03:00〜21:15 に散っているのに報告値は一定 → 定数フォールバックの直接証拠。

kalman_d7 の session 窓は `(h<7) or (7<=h<12) or (16<=h<21)` であり、
**h=12 はこの窓の唯一の穴**。よって live 発火確率は市場条件に関わらず **恒等的に 0**。
2026-05-28 の LIVE 化以降 **73 日 0 fire** は市場のせいではなく構造ブロックだった。

> ⚠️ これにより、`pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28.md` の
> 2026-05-29 判定「INCONCLUSIVE = 設計対象外局面」は**誤診**と確定する。
> 当時 DIST filter fail と読んだ 2 バーは事実だが、仮に DIST を通過していても
> session gate で必ず落ちていた。T9 追補が用意した判定表の
> 「>0, 全 emit=False → (b) filter 落ち」に該当するが、その filter が
> **市場条件ではなく凍結した定数**だった、という第 4 の分類が必要だった。

### 3.2 自然実験 — 回避策を持つ戦略との対照

一部の戦略は `ctx.hour_utc` を使わず `ctx.df.index[-1].hour` から自前導出している
(`turtle_soup.py:284-287`, `london_session_breakout.py:255`、いずれも redesign_v2 経路)。
同一エンジン・同一 tick で走るため、**唯一の差分が hour の取得元**という対照群になる。

本番 trades API (2026-06-19〜08-07) で、各戦略の BT 窓に対する「窓外発火」を計数:

| 群 | 戦略 | BT 窓 (UTC) | N | 窓外 | 窓外率 |
|---|---|---|---|---|---|
| **A** `ctx.hour_utc` 直読み | squeeze_release_momentum | 7≤h<17 | 75 | 65 | 86.7% |
| A | inducement_ob | 7≤h<20 | 15 | 4 | 26.7% |
| A | liquidity_sweep | 6≤h<20 | 4 | 2 | 50.0% |
| A | trendline_sweep | 6≤h<20 | 143 | 12 | 8.4% |
| **A 計** | | | **237** | **83** | **35.0%** |
| **B** bar-time 自前導出 | turtle_soup (v2) | 6≤h<20 | 15 | 0 | 0.0% |
| B | london_session_breakout (v2) | 7≤h≤9 | 13 | 0 | 0.0% |
| **B 計** | | | **28** | **0** | **0.0%** |

**Fisher exact (one-sided) p = 1.32e-05**

群 A の窓外率が戦略ごとに違うのは、窓の広さと素シグナルの時刻分布の差で説明できる
(trendline_sweep の窓 6-20 は 1 日の 58% を覆うので、ゲート無効化の可視率が低い)。
群 B が 0/28 であることが、ゲート自体は機能しうる = 差分が hour 取得元であることを示す。

### 3.3 発火ゼロ群 (窓が h=12 を含まない戦略)

以下は API 窓 (50 日) で **live/shadow 発火が完全にゼロ**:

| 戦略 | 窓 (UTC) | h=12 |
|---|---|---|
| kalman_d7 (3 variant) | h<7 \| 7≤h<12 \| 16≤h<21 | ❌ |
| pd_eurjpy_h20_bbpb3_sell | h==20 | ❌ |
| tokyo_range_breakout | 7≤h<9 | ❌ |
| london_ny_swing | 13≤h≤17 | ❌ |
| tokyo_nakane_momentum | 00:45–01:15 (分解像) | ❌ |

発火ゼロは「エッジが無い」ではなく「**評価されていなかった**」。

---

## 4. ロードマップへの含意

### 4.1 ボトルネックへの直撃

roadmap v2.3 のボトルネックは「正の摩擦調整 EV セルの不在」であり、その手前の律速は
**クリーン N の蓄積**。本バグは供給側を二重に殺していた:

1. 窓が h=12 を含まない戦略 → shadow N が構造的にゼロ (探索母集団から消えていた)
2. 窓が h=12 を含む戦略 → BT 窓外の汚染サンプルが N に混入

「内部母集団の供給枯渇を三重確認」([[external-hypothesis-scan-2026-07-13]]) という
過去の結論は、**枯渇の一部が観測装置の故障だった**可能性を含む。ただし WS3 の
FAIL 判定群 (lfr / htf_fb / T10 / T11) は BT/探索側の解析であり bar_time を持つため、
それらの verdict 自体は本バグの影響を受けない。影響を受けるのは
**live/shadow 発火数に依拠した判断**のみ。

### 4.2 clean live 負エッジ (−242.6p / payoff 0.274) との関係

群 A の 35.0% は「BT が一度も検証していない時間帯で発火した live トレード」。
金曜ブロック (`FRIDAY_BLOCK_HOUR` 13〜18) が live で一度も効いていなかったことも
併せると、live 劣化の一部は**エッジの消滅ではなく執行窓の逸脱**で説明されうる。
本修正後に clean live を再計測することで、この寄与分を分離できる。

> 定量化は本ドキュメントの範囲外 (再計測は修正デプロイ後 N 蓄積を待つ)。
> ここでは「negative live EV の説明変数として新規に 1 つ追加された」ことのみ記録する。

---

## 5. 修正

`app.py` の DT ctx 構築を `is_trade_prohibited` / `SignalContext.from_df` と同じ
降り方に揃えた:

```python
if bar_time is not None and hasattr(bar_time, 'hour'):
    _dt_bar_dt = bar_time                    # BT: 明示バー時刻 (契約不変)
elif <df.index 末尾が時刻を持つ>:
    _dt_bar_dt = df.index[-1]                # live: 直近バー時刻
else:
    _dt_bar_dt = datetime.now(timezone.utc)  # 最終手段
# naive は UTC 扱い / aware は UTC へ正規化
_dt_hour_utc = _dt_bar_dt.hour
_dt_is_friday = _dt_bar_dt.weekday() == 4
```

`modules/data.py` が fetch 経路の index を UTC に正規化済みのため、
live の `df.index[-1].hour` は UTC 時刻。

**回帰テスト**: `tests/test_dt_ctx_hour_utc_live.py` (9 件)
修正前のコードに対して 7 件が失敗することを確認済み (テストの有効性検証)。

---

## 6. 修正の作用方向 (影響評価)

| 方向 | 戦略 | 効果 | リスク評価 |
|---|---|---|---|
| **制限** | trendline_sweep / squeeze_release_momentum / inducement_ob / liquidity_sweep / post_news_vol / jpy_basket_trend (加点) / ema200_reversal (trend_v2) | 窓外発火が止まる + 金曜ブロック復活 | **安全** — BT 検証済み設計への復帰 |
| **開放** | pd_eurjpy_h20 / tokyo_range_breakout / london_ny_swing / tokyo_nakane_momentum | shadow N の蓄積が始まる | **安全** — shadow のみ (原則4: データ蓄積優先) |
| **開放 (要監視)** | **kalman_d7 × 3 variant** | `KALMAN_D7_LIVE_ENABLE=1` (本番 effective) のため **live 発火が始まる** | ⚠️ 下記 |

### kalman_d7 の扱い

- live 化は **2026-05-28 に user が option B で明示決裁**済み (lot 0.5× / 3 variant 同時 = 1.5× base)。
  退避条件も同 pre-reg に明記済み (Live N≥10 で EV<0 → 0.1× 降格 / 連続 3 SL で user review)。
- 本修正は「user が承認した設計を初めて実際に動かす」ものであり、**新規昇格ではない**
  (Rule 1 の対象外)。Claude 側で勝手に demote するのは user 決裁の上書きになるため行わない。
- ただし決裁から **73 日**が経過し、その間の live N は 0 のまま。
  → 退避条件を**機械監視に載せる**ため `prereg-trigger-registry.json` に
  `t9-kalman-d7-live-n10-ev-check` を新設 (T5 教訓「pre-reg には監視主体を必ず併設」)。

---

## 7. 教訓

1. **「分母なき 0-fire は必ず計装せよ」は正しかったが、計装値そのものを疑う枠が無かった。**
   QUALBAR は 2026-07-06 に導入され、その時点から `hour=12` を出力し続けていた。
   判定表に「観測値が定数に張り付いていないか」の欄が無かったため 34 日読み飛ばされた。
   → **テレメトリの判定表には「値が動いているか」の健全性チェックを必ず入れる。**

2. **同一関数内に正しい実装と壊れた実装が同居しうる。**
   `is_trade_prohibited` は 4 行上で正しく `now()` に降りていた。
   → 同じ入力 (`bar_time`) を複数箇所で解釈する関数は、**降り方を 1 つのヘルパに正規化**する。

3. **戦略側の回避策は、基盤バグの症状として読め。**
   `turtle_soup` / `london_session_breakout` が `ctx.hour_utc` を信用せず
   `df.index` から取り直していたのは、誰かが症状に気づいた痕跡だった。
   → **同じ値を別経路で取り直すコードを見たら、元の経路のバグを疑う。**

4. **「context fix」は再発する。** 2026-04-04 に直った同型バグが 4 日後に再混入した。
   → 回帰テストを同時に入れていれば 123 日ではなく 4 日で検出できた。

---

## References

- 修正 PR: `fix/dt-ctx-hour-utc-live-2026-08-09` [rule:R3]
- 退行元: `9c849cef` (2026-04-08) `feat(v6.7): DT構造改革`
- 誤診の訂正対象: [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] §6.5
- 関連: [[bt-live-divergence]] / [[roadmap-v2.3-payoff-friction-repair]]
- 同型教訓: [[lesson-reactive-changes]] (「1日データで対策実装は禁止」ではなく、
  ここでは逆に「123 日の 0 件を放置した」型) / MEMORY `project_engine_reconstruction_live_dedup_dead`
