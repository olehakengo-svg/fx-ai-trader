# 教訓: カウンタが「測っていない量」を名乗ると、監視は 8 日間その名前を追いかける

**日付**: 2026-09-05 / **Rule**: R3
**実例**: [[rnb-dead-mode-and-block-estimand-2026-09-05]]

---

## 何が起きたか

`rnb_usdjpy:direction_filter` が本番 block 集計の **15.6% (第 4 位 family)** を占め、
2026-08-26 → 09-04 の **8 回連続**で監視ログの 🔴 に載り続けた。
仮説は毎回「`compute_rnb_signal` の WAIT-path バグ」。

実体は**バグではなくラベル**だった。この gate は

- 「方向が逆 (SELL が来たが BUY-only)」
- 「そもそもシグナルが無い (WAIT)」

を**同じカウンタ名**で数えていた。そして `direction_filter` を持つ唯一のモードの signal_fn は
**SELL への return path を構造上持たない** (12.8y / 315,623 バー実測で SELL=0)。
⇒ このカウンタの中身は **恒久的に 100% が WAIT**。
「方向棄却」という名前が指す量を、**一度も測っていなかった**。

## なぜ 8 日かかったか

数字は毎日読まれていた。**名前が信用されていた**。
`direction_filter` が 100% なら「方向判定が壊れている」と読むのが自然で、
その読みが正しくない可能性 —「そもそもこのモードは SELL を出せない」— は
**カウンタ名からは見えない**。コードを 1 度読めば 10 分で終わる確認が、8 日回った。

さらに副作用として、`direction_filter` が block chain の**最初**にあるため
WAIT が本来落ちるはずの `conf<30` に到達せず、`conf<30 = ZERO` という
**それ自体が異常に見える観測**を生み、仮説をさらに補強していた。

## ルール

1. **カウンタ名は estimand の宣言である。** 名前が指す量と、その分岐が実際に捕まえる集合が
   一致しているかを、名前を付けた時点で確認する。
   一致しないなら **分岐を分けるのではなく、ラベルを分ける** (制御フローを触らずに済む)。
2. **「その分岐に到達しうる入力の集合」を signal_fn 側から確認する。**
   本件は「SELL は構造上到達不能」を関数の return literal から確定できた。
   到達不能な条件を数えるカウンタは、恒久的に補集合だけを数える。
3. **8 回同じ 🔴 が出たら、数字ではなく数字の定義を疑う。**
   繰り返し発火する監視項目は「本物の異常」か「壊れた estimand」のどちらかで、
   後者は回数を重ねるほど確信を強めてしまう (誤った収束)。
4. **構造 pin は「性質」を書く** (MEMORY `project_freshness_ui_ssot_pin_property_2026_08_29` の 3 例目)。
   本件の pin は「`compute_rnb_signal` の signal literal 集合 == {WAIT, BUY}」。
   SELL path が足された瞬間に落ち、その時点で初めて `direction_filter` が
   非ゼロの意味を持つので監視の読み方を更新させられる。

## 同時に見つかった同型 (読み手不在)

`rnb_support_bounce` が `QUALIFIED_TYPES` 未登録のまま `auto_start: True` で **153 日**動いていた。
既存テスト `tests/test_preserve_types_tick_entry.py` は
"NOT in QUALIFIED_TYPES … pins that current behavior" と**事実を正確に記録**していたが、
それを**意図された設計として固定**しており、異常として上申する読み手がいなかった。

→ **「現状を pin する」テストは、その現状が意図か事故かを本文に書く。**
   事故なら pin は「検出可能性の固定」であって「正しさの固定」ではない、と明示する。
   本件の恒久ガードは既知ドリフト集合との **完全一致 (== / ⊆ ではない)** で assert し、
   **解消側にもテストが落ちる**ようにした。

## 関連

- [[m1-kpi-readout-and-mechanical-flip-2026-09-04]] — KPI の読み手不在 (同型の上位版)
- [[lesson-kpi-without-a-reader-2026-09-04]]
- MEMORY `project_monitoring_blind_during_outage_2026_08_30` — 「静かだった」と「見えていなかった」の区別
- MEMORY `project_row_freshness_candidate_cadence_2026_08_27` — `no_rows` と `error` を折り畳むな
- MEMORY `project_live_fill_estimand_shadow_conflation_2026_09_03` — 名乗る estimand を測っているか
