---
tags: [analysis, estimand-audit, monitoring, m3, rule-r3]
date: 2026-09-10
rule: R3
supersedes_claim_in: [[live-roster-attrition-2026-09-06]]
registry: roster-attrition-88pct-estimand-audit
---

# D クラス estimand 監査 — 「本来出てはいけなかった発火」は 15 セル中 1 セルだった

**verdict: 旧解釈を棄却。静的方針に反する発火は 1 セル 2 約定のみ**

> ⚠️ **2026-09-10 改訂 (PR #230 Codex P1 ×2)**: 初版は「26/28 約定は正当」と書いたが、
> (a) 降格集合の不在から昇格方針を**推論**していた (04-02 の発火は `_is_promoted` が
> そもそも存在しない時期で、根拠が別物だった) (b) `_is_promoted` は既定 return より
> **手前**で `get_strategy_mode()` と `_promoted_types` を見るため**ブロック方向**の
> ランタイム自由度があり、「LEGIT 側は override に不感」は成り立たなかった。
> 方針を AST で再構成し直し、verdict 名に条件性を持たせて §4 を改訂した。

## 0. 監査の起点

registry `roster-attrition-88pct-estimand-audit` (期日 2026-09-22)。
出所は **PR #226 の Codex P1 finding #2** — レビュー到着の直後にマージされ
未読だった 2 件のうち 1 件 ([[pr-review-gate-2026-09-08]] が実測した
「独立レビューは 5.5 ヶ月 write-only」の実害の一部)。指摘:

> `D_NEVER_PROMOTED` 判定は「**現在**の昇格集合に不在」を
> 「anchor 日も未昇格」と読み替えている。

user 恒久指示 (MEMORY `feedback_audit_past_verdicts_2026_08_05`
「過去 verdict 自体を疑え」) の適用事例。

## 1. 指摘は成立する — 欠陥は D に局在する

`tools/live_roster_attrition.py` の `load_stop_sets()` は **HEAD の**
`modules/demo_trader.py` / `strategies/daytrade.py` を読む。これは
**B/C/E については正しい estimand** — 3 クラスはいずれも「**今**なにが
このセルを止めているか」という現在形の問いに答えるからである。

D だけが**過去形の主張**を運んでいた:「昇格集合に一度も入っていないのに
LIVE 約定を出していた = 本来出てはいけなかった発火」。この主張の根拠は
現在の集合だけで、当時の昇格状態については何も測っていない。

さらに、分類器は当時存在した LIVE 資格集合のうち
`_PAIR_PROMOTED` / `_UNIVERSAL_SENTINEL` の 2 本しか見ていない。
anchor 窓当時 (2026-04) の `demo_trader.py` には他にも

| 集合 | 役割 | 現 HEAD |
|---|---|---|
| `_ELITE_LIVE` | Phase-0 shadow gate の免除 (type 単位) | **消滅** |
| `_GRAIL_CANDIDATES` | filter 合致で shadow gate 全段 bypass (0.01 lot) | 残存・未参照 |
| `_C1_PROMOTE_CANDIDATES` | 同 (Bonferroni 有意セル) | 残存・未参照 |
| PRIME tier A/B (`modules/prime_gate.py`) | pre-reg override で LIVE 昇格 | — |
| `_SCALP_SENTINEL` | lot / gate 免除 | 残存・未参照 |

が存在した。`_ELITE_LIVE` は現 HEAD に**存在しない**ので、当時 ELITE だった
セルは自動的に D か E に落ちる。

## 2. 実測 — 全 15 セルの発火は tier gate 導入前に閉じていた

読み手: `tools/roster_d_class_estimand_audit.py` (約定 1 件ごとに、
**その時刻に本番に載っていた commit** を `origin/main` の first-parent
履歴から特定し、`_FORCE_DEMOTED` / `_PAIR_DEMOTED` を AST で読む)。

D 15 セルの clean LIVE 約定 28 件の実測レンジ = **2026-04-02 〜 04-14T02:54Z**。
Phase-0 三層化 (`_SHADOW_MODE` + `_ELITE_LIVE` + Phase0 tier gate) の導入は
commit `293165ef` **2026-04-14T08:16:58Z**。つまり **28/28 件すべてが
gate 導入前**である。

クラス別の gate 前後分解 (全 124 セル):

| class | 約定 gate 前 | 約定 gate 後 | セル: gate 前のみ | セル: gate 後を含む |
|---|---:|---:|---:|---:|
| `B_LIVE_STOPPED` | 524 | 85 | 35 | **48** |
| `C_SHADOW_DEMOTED` | 46 | 8 | 6 | 6 |
| **D** | **28** | **0** | **15** | **0** |
| `E_PROMOTED_UNATTRIBUTED` | 21 | 13 | 5 | 9 |

**完全分離**。B は 48/83 セルが gate 後も発火しており、列挙済みの降格機構で
実際に止まっている (帰属は妥当)。D だけが gate 前に閉じている。

## 3. gate 前は allow-by-default だった

gate 直前 commit (`293165ef^` = `b33d579f`) の `_is_promoted()`:

```python
        # v6.2: OANDA送信は許可。N<10の未検証戦略はSentinel lotで保護
        # (ロット計算側の _is_sentinel 判定で 0.01lot 化される)
        return True
```

すなわち `_FORCE_DEMOTED` / `_PAIR_DEMOTED` / 自動降格に載っていなければ
**LIVE 送信が設計状態**だった。さらに 2026-04-03 の commit `8a42d776` は
コミットメッセージ自体が
**"temp: disable OANDA strategy promotion filter — send all entries to OANDA"**
で、当時の `_is_promoted()` は
`return True  # 一時的に全戦略をOANDA送信` だった (降格集合はコード上に
まだ存在しない)。

## 4. verdict — 約定 1 件ごとの判定 (2026-09-10 改訂版)

判定は**降格集合の不在から推論せず**、約定時刻の `_is_promoted()` を AST で
読んで方針そのものを分類する (`promotion_policy_at`)。実測 28 約定の方針内訳 =
`ALLOW_BY_DEFAULT` 23 / `ALL_SEND` 3 / `NO_GATE` 2 (`DENY_BY_DEFAULT` と
`UNKNOWN` は 0)。

| 判定 | セル | 約定 | ランタイム状態 |
|---|---:|---:|---|
| `PERMITTED_NO_GATE` (昇格ゲート未実装、OANDA ミラー無条件) | 1 | **2** | **不感** |
| `PERMITTED_ALL_SEND` (`_is_promoted` が `return True` 単文) | 2 | **3** | **不感** |
| `PERMITTED_STATIC_RUNTIME_UNKNOWN` (allow-by-default + 静的降格集合に不在) | 11 | 21 | ⚠️ 条件付き |
| **`CONTRADICTS_STATIC_DEMOTE`** | **1** | **2** | — |
| `DENY_BY_DEFAULT_UNEXPLAINED` / `POST_GATE_UNEXPLAINED` / `UNRESOLVED_NO_CODE_STATE` | 0 | 0 | — |

**無条件に「許可されていた」と確定した約定 = 5 / 28。**
残り 21 約定は「**静的コードは許可していた**が、ランタイム降格状態が
再構成不能」という条件付き。静的方針に反するのは 2 約定
(`dual_sr_bounce × USD_JPY × BUY`、2026-04-13T13:01Z / 16:01Z、当時
`_FORCE_DEMOTED` 在籍) のみ。

### 4.1 なぜ「条件付き」なのか (初版の誤りの訂正)

`_is_promoted()` の allow-by-default 形 (v6.2) は既定 `return True` に至る前に
**2 つのランタイム照会**を持つ:

1. `self._oanda.get_strategy_mode()` — `"off"` ならブロック、
   `"live"`/`"sentinel"` なら全降格を上書き (**両方向**)
2. `self._promoted_types[et]["status"] == "demoted"` — **ブロック方向のみ**

初版は 1 の上書き方向だけを見て「LEGIT 側は override に不感 = 結論の向きは
非対称に安全」と書いたが、**2 と 1 の "off" はブロック方向**なので成り立たない。
いずれも DB / メモリ状態で git から再構成できないため、
`PERMITTED_STATIC_RUNTIME_UNKNOWN` は条件付き判定である。
無条件に確定するのは `PERMITTED_NO_GATE` と `PERMITTED_ALL_SEND` の 2 verdict
だけ (この 2 つは既定 return より手前に照会が無い / 照会するコード自体が無い)。

### 4.2 それでも旧解釈は棄却される

条件性を認めても、旧主張「昇格集合に**一度も**入らずに LIVE 約定を出していた =
既知の昇格バグの残響」は成立しない。理由:

- 旧主張の**根拠**は「現在の昇格集合に不在」だけで、当時の状態を測っていない
  (これは条件性とは無関係な、evidence そのものの誤り)
- 5 約定は**無条件に**設計状態と確定した (ゲート未実装 / 全送信期)
- 21 約定は静的方針が許可しており、ブロックされたと考える積極的な理由が無い
  (ランタイム降格が起きていたなら約定が成立しないので、**約定が存在すること
  自体**が「そのとき通った」ことは示す。ただしそれは「通ったのが設計か
  バグか」を分けないので、条件付きに留める)
- 静的方針に反する = バグ候補は **1 セル 2 約定**

## 5. 引用可否の改定

| 主張 | 改定 |
|---|---|
| 「帰属済み 88.7%」(124 セル中 110) | ✅ **引用可・数値不変**。D も帰属済みのままで、帰属**先の機構**が変わるだけ (列挙されていなかった第 5 の停止機構 = 2026-04-14 の Phase-0 tier gate) |
| 「停止済み 83 セルは anchor 窓で N=609 / −469.8p」 | ✅ 引用可 (B の gate 後発火 48 セルで裏づけ) |
| **「D 15 セルは過去の昇格バグの残響 = 本来出てはいけなかった発火」** | ❌ **棄却**。静的方針に反するのは **1 セル 2 約定**のみ。5 約定は無条件に設計状態と確定、21 約定は静的コードが許可 (ランタイム降格は再構成不能なので条件付き)。⚠️ 初版の「26/28 は正当」は言い過ぎで、正しくは「無条件確定 5 / 条件付き 21 / 反する 2」 |
| **「D 15 セルは M3 の分子に数えてはならない」** | ⚠️ **根拠が変わる**。「バグだから除外」は不成立。正しくは「**2026-04-14 の tier 設計変更で意図的に live 資格を外されたセル**」であり、分子に含めるか否かは**バグ判定ではなく政策判断** (この 15 セルを再昇格させる意思があるか)。ただし経済的インパクトは **N=28 / −26.2p** で無視可能なので、M3 の ~14 ヶ月 ETA および [[friction-adjusted-ev-map-2026-07-07]] の結論はいずれの扱いでも変わらない |

## 6. コード側の是正 (同一コミット)

- `D_NEVER_PROMOTED` → **`D_NOT_LIVE_ELIGIBLE_NOW`**。クラス名が過去形の
  主張を運ばないようにした (旧称の復活は pin で防止)
- subclass `D1_PRE_TIER_GATE` / `D2_POST_TIER_GATE` を新設 — 「gate 前だけ」と
  「gate 後を含む」は**別の問い**で、後者だけが当時の昇格集合の再構成を要する
- docstring に旧解釈の棄却と監査ツールへの導線を明記
- `tools/roster_d_class_estimand_audit.py` 新設 (再実行可能な読み手)。
  約定 1 件ごとに `promotion_policy_at()` で `_is_promoted()` の**既定**を
  AST 分類し (`NO_GATE` / `ALL_SEND` / `ALLOW_BY_DEFAULT` / `DENY_BY_DEFAULT` /
  `UNKNOWN`)、`UNKNOWN` は許可側でなく `UNRESOLVED` に流す。
  現 HEAD の `_is_promoted` は `_is_promoted_ex(...)["allowed"]` への委譲形で
  `UNKNOWN` になるが、これは保守側の挙動なので意図どおり。
  ⚠️ 実装中に**自分で同型の欠陥を作りかけた** — `demote_sets_at` が
  「読めたが集合が無い」を `None` (= 読めなかった) に折り畳んでおり、
  5 約定が UNRESOLVED に化けていた。これは 2026-08-30 の
  `fetch_json` blind ([[project_monitoring_blind_during_outage_2026_08_30]])
  と同型。関数の契約をテストで pin (合成 cache を注入するテストは関数を
  迂回するので検出できない — **契約は関数で pin する**)

## 6.1 registry entry の resolve は PR #227 マージ後

registry entry `roster-attrition-88pct-estimand-audit` は **PR #227
(`fix/review-gate-trigger-watch`) のブランチにのみ存在し、まだ main に
到達していない**。したがって本コミットでは resolve できない。
**PR #227 がマージされた直後に、本監査の結論で `active: false` +
`resolved: 2026-09-10` + resolution を書き込むこと** (同一セッション内で
実施 — 「commit した ≠ 永続化」の教訓により main 到達まで追う)。

## 6.2 `attributed_share` から D2 を除外 (PR #230 Codex P2)

`--anchor` を tier gate 後に動かすと D2 (要説明) が現れるが、
`explained` は D クラス全体を数えていたため share を黙って膨らませていた。
**D1 のみ**を帰属済みに数えるよう修正 (pin 併設)。既定 anchor (2026-05-01) では
D は 15/15 が D1 なので **88.7% の数値は不変**。

## 7. 教訓

**現在形の集合で過去形の主張をするな。** クラス名は estimand を運ぶ —
`D_NEVER_PROMOTED` という名前自体が、根拠 (「今の集合に不在」) より
強い主張 (「当時も不在」) を毎回の readout で再生産していた。
分類器を書くときは、各クラスが**現在形の問いか過去形の問いか**を
docstring で宣言し、過去形なら当時のコード状態を再構成する主体を
同じコミットで併設せよ。

**そして「不在」から方針を推論するな。** 初版は「降格集合が無い ⇒ allow-by-default」と
推論したが、それが示すのは「その 2 定数が無かった」だけだった (2026-08-31 の
「組み立てた URL の 404 は不在の証拠ではない」と同型の推論誤り)。
**方針を主張するなら方針そのもの (`_is_promoted` の実体) を読め。**

**限界は verdict 名に書け。** 「LEGIT」という名前は無条件の含意を運んでしまう。
`PERMITTED_STATIC_RUNTIME_UNKNOWN` のように条件を名前に埋めると、
readout を引用する側が限界を落とせない。

関連: [[live-roster-attrition-2026-09-06]] / [[pr-review-gate-2026-09-08]] /
[[process-meta-audit-2026-09-07]] / [[lesson-validity-check-pins-proxy-2026-09-02]]
