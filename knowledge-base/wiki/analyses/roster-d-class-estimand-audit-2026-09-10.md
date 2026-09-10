---
tags: [analysis, estimand-audit, monitoring, m3, rule-r3]
date: 2026-09-10
rule: R3
supersedes_claim_in: [[live-roster-attrition-2026-09-06]]
registry: roster-attrition-88pct-estimand-audit
---

# D クラス estimand 監査 — 「本来出てはいけなかった発火」は 15 セル中 1 セルだった

**verdict: 旧解釈を棄却 (14/15 セル・26/28 約定は当時の設計どおり LIVE 可)**

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

## 4. verdict — 約定 1 件ごとの判定

| 判定 | セル | 約定 |
|---|---:|---:|
| `LEGIT_ALLOW_BY_DEFAULT` (gate 前・降格集合に不在) | 11 | 21 |
| `LEGIT_NO_DEMOTE_MECHANISM` (降格機構がコードに未実装の時期) | 3 | 5 |
| **`ILLEGIT_DEMOTED_AT_FIRE`** | **1** | **2** |
| `POST_GATE_UNEXPLAINED` | 0 | 0 |
| `UNRESOLVED_NO_CODE_STATE` | 0 | 0 |

唯一の違反は **`dual_sr_bounce × USD_JPY × BUY`** の 2 約定
(2026-04-13T13:01Z / 16:01Z)。当時デプロイされていた `4011b94d` /
`57536285` で `dual_sr_bounce` は `_FORCE_DEMOTED` に在籍していた。
同セルの 3 件目 (04-07T05:45Z) は在籍前なので LEGIT。

⚠️ **limitation**: `_is_promoted()` は静的集合より**先に**
`self._oanda.get_strategy_mode()` を見て "live"/"sentinel" なら全降格を
上書きする。これはランタイム DB 状態で git から再構成できないため、
ILLEGIT 判定は「手動 mode override が無かったならば違反」という条件付き。
逆に LEGIT 側はこの自由度に影響されない (override は LIVE 方向にしか
効かない) ので、**結論の向きは非対称に安全** — 「14/15 は正当」は
override の有無に関わらず成立する。

## 5. 引用可否の改定

| 主張 | 改定 |
|---|---|
| 「帰属済み 88.7%」(124 セル中 110) | ✅ **引用可・数値不変**。D も帰属済みのままで、帰属**先の機構**が変わるだけ (列挙されていなかった第 5 の停止機構 = 2026-04-14 の Phase-0 tier gate) |
| 「停止済み 83 セルは anchor 窓で N=609 / −469.8p」 | ✅ 引用可 (B の gate 後発火 48 セルで裏づけ) |
| **「D 15 セルは過去の昇格バグの残響 = 本来出てはいけなかった発火」** | ❌ **棄却**。実際は 14/15 セル (26/28 約定) が当時の設計どおり LIVE 可。バグ由来と言えるのは 1 セル 2 約定のみ (かつ override 前提付き) |
| **「D 15 セルは M3 の分子に数えてはならない」** | ⚠️ **根拠が変わる**。「バグだから除外」は不成立。正しくは「**2026-04-14 の tier 設計変更で意図的に live 資格を外されたセル**」であり、分子に含めるか否かは**バグ判定ではなく政策判断** (この 15 セルを再昇格させる意思があるか)。ただし経済的インパクトは **N=28 / −26.2p** で無視可能なので、M3 の ~14 ヶ月 ETA および [[friction-adjusted-ev-map-2026-07-07]] の結論はいずれの扱いでも変わらない |

## 6. コード側の是正 (同一コミット)

- `D_NEVER_PROMOTED` → **`D_NOT_LIVE_ELIGIBLE_NOW`**。クラス名が過去形の
  主張を運ばないようにした (旧称の復活は pin で防止)
- subclass `D1_PRE_TIER_GATE` / `D2_POST_TIER_GATE` を新設 — 「gate 前だけ」と
  「gate 後を含む」は**別の問い**で、後者だけが当時の昇格集合の再構成を要する
- docstring に旧解釈の棄却と監査ツールへの導線を明記
- `tools/roster_d_class_estimand_audit.py` 新設 (再実行可能な読み手)。
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

## 7. 教訓

**現在形の集合で過去形の主張をするな。** クラス名は estimand を運ぶ —
`D_NEVER_PROMOTED` という名前自体が、根拠 (「今の集合に不在」) より
強い主張 (「当時も不在」) を毎回の readout で再生産していた。
分類器を書くときは、各クラスが**現在形の問いか過去形の問いか**を
docstring で宣言し、過去形なら当時のコード状態を再構成する主体を
同じコミットで併設せよ。

関連: [[live-roster-attrition-2026-09-06]] / [[pr-review-gate-2026-09-08]] /
[[process-meta-audit-2026-09-07]] / [[lesson-validity-check-pins-proxy-2026-09-02]]
