# 🔒 Pre-reg LOCK: GBP_USD 素fade版 × 本番メカニクス (m=1 単発判定) — 2026-06-12

**MEMORY:** `project_hull_donchian_multipair_prereg_2026_06_12.md`
**LOCK 規律**: 本節の spec・gate・spread を実行前に凍結。実行後の変更・grid 探索・
パラメータ再調整は禁止。結果は PASS/FAIL を問わず本ファイルに append。一発判定 (no iteration)。

## なぜこの単発 pre-reg を起こすか

横展開 pre-reg ([[hull-donchian-fade-multipair-prereg-2026-06-12]]) とは独立の宿題。
GBP_USD は過去に **素の fade 版** (width 圧縮ゲート無し / opposite-exit) で
C1-C4 を通過済み (N=8572 / net+0.673p / PF1.057 / WF3/4、
`reports/prereg_15m_fade.txt`) だが、**opposite-exit で検証されたまま本番メカニクス
(TP=static basis / SL=4×ATR / hold96) では未検証**で眠っている。

LIVE 候補にするには production harness が使う唯一の exit = fidelity メカニクスで
成立するかを確認する必要がある。これは grid 探索ではなく「検証済みエッジを本番
メカニクスに写像できるか」の一発確認。criteria を実行前に凍結することで post-hoc 罠を回避。

**重要な区別**: width 圧縮ゲート**付き**の GBP_USD は holdout で既に REJECT 済
(`decisions/hull-donchian-fade-live-2026-06-12.md`)。本 pre-reg は width ゲート**無し**の
素 fade のみを対象とする。両者を混同しない。

## 凍結 spec

- entry: Hull(HMA55) trend × Donchian(20) 二重確認 fade、**width ゲート無し** (全 fade bar)
- exit (fidelity): TP=entry-bar Donchian basis (static, intrabar limit) /
  SL=4×ATR14 intrabar SL-first / max_hold 96 bars → close。TP/SL サイド sanity gate あり
- flat 時のみ entry、pyramiding なし。entry=シグナル bar close
- pair=GBP_USD、data=MASSIVE 15m ~12.4y (cache 既存)、pip=0.0001
- spread=**1.2p** round-turn (前回素fade pre-reg と同一、凍結)

## 判定条件 (ALL required, m=1 のため FDR ではなく素の有意性、実行前凍結)

- C1: net EV > 0
- C2: bootstrap p (10k, seed=42, one-sided mean>0) < 0.05
- C3: walk-forward 4 等分時間 fold で ≥3/4 fold net 正
- C4: Wilson 95% lower bound (WR) > 損益分岐 WR
- C5: LONG / SHORT 両 side net EV > 0

**報告のみ**: regime (trailing-90d UP/DOWN) × side / exit-reason 構成 / 保有 /
>=2022 サブ期間 / spread +0.3p ストレス。

**PASS → LIVE 候補として user 決裁** (shadow-first 例外は user 判断)。**FAIL → 棄却、棚卸し完了**。

## 結果 (2026-06-12 実行、verdict 確定 — 再調整禁止)

**REJECT。** raw output: `hull-donchian-1m-validation/reports/prereg_gbpusd_rawfade_fidelity.txt`

GBP_USD 2014-2026, N=7888, WR=.679, net EV=+0.688p, PF=1.049, p=0.0659, Wilson_lo=.668 vs BE=.668, maxDD=5390p

| gate | 結果 |
|---|---|
| C1 netEV>0 | ✅ +0.688p |
| C2 bootstrap p<0.05 | ❌ p=0.0659 |
| C3 WF ≥3/4 | ❌ 2/4 (F1 −1.14p / F2 −0.82p / F3 +3.75p / F4 +1.08p) |
| C4 Wilson>BE | ✅ (辛うじて、.668 vs .668) |
| C5 両side EV>0 | ❌ LONG −0.124p (PF0.99) / SHORT +1.475p |

### 所見

1. **opposite-exit で通った C1-C4 は本番メカニクスに transfer しない**。素fade の見かけの
   エッジは exit メカニクス依存だった (opposite-exit 版 net+0.673p → fidelity 版でも
   net+0.688p と総額は近いが、WF・両side・有意性が全て崩れる)。
2. **横展開 4ペアと完全同型の時間構造**: F1/F2 (2014-2020) 負、F3/F4 (2020-2026) 正。
   SHORT も regime 分解で UP −0.31p / DOWN +3.11p = 直近の GBP 下落局面に集中。
   LONG は全 regime 負。
3. **>=2022 単独なら +3.21p/PF1.248** と見栄えするが、これは EUR_GBP/USD_CHF と同じ
   直近窓集中で、昇格根拠にはできない ([[feedback_cohort_time_check]])。

### 帰結

GBP_USD は素fade・width-gate版とも全 exit で本番投入不可と確定。**この戦略ファミリで
LIVE 投入できるのは EUR_USD (全期間 4/4 fold 正) 単体のみ**という横展開 pre-reg の結論を
独立に再確認した。GBP_USD 宿題はクローズ。
