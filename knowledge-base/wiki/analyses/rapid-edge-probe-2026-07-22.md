# rapid_edge_probe — S2 (R3 診断) 共通ハーネス 使い方 (2026-07-22)

> **位置づけ**: [[edge-development-pipeline-2026-07-18]] §2 **S2** の標準ツール。user 要求
> (2026-07-22「仮説を爆速で実装してテストするフロー」) への回答。仮説スペック 1 ファイル →
> 探索窓のみの標準診断レポート (md+json) を数十秒で出す。rule:R3 (純研究、live 変更なし)。
> **探索診断 ≠ 判定 — 本ツールの出力から live/tier 判断は禁止** (レポートヘッダに自動印字)。

## 1 コマンド

```bash
python3 tools/rapid_edge_probe.py run --spec tools/rapid_probe_specs/{name}.json
python3 tools/rapid_edge_probe.py run --spec ... --draft-prereg   # S3 pre-reg スケルトン自動 draft
python3 tools/rapid_edge_probe.py self-test                        # 合成データ dry-run (data 不要)
```

出力: `knowledge-base/raw/bt-results/rapid_probe_{name}_{date}.{md,json}` /
draft: `knowledge-base/wiki/decisions/prereg-draft-{name}-{date}.md` (🔓 DRAFT、LOCK 不能な TODO 付き)。

## スペック小語彙 (これ以外は即 ValueError)

```jsonc
{
  "name": "my_hypothesis",                       // [a-zA-Z0-9_]+
  "description": "...", "notes": "...",
  "direction_source": {
    "kind": "event | series | technical",
    // event    : {"event": "NFP|CPI|FOMC", "rule": "fade|follow|uncond_usd_long|uncond_usd_short", "w0_min": 30}
    // series   : {"column": "...", "file": "csv (date + per-pair列 or column単列)", "lag_days": 1}
    //            column "__dummy" 始まり = 決定的ダミー±1 (E20 接続前の構造検証専用)
    // technical: {"condition": "momentum_sign|ema_trend", "lookback"|"fast"+"slow"}
  },
  "entry_trigger": {"kind": "none | breakout | pullback", "lookback": 20, "ema_period": 20, "search_bars": 16},
  "pairs": ["USD_JPY", ...],                     // 摩擦テーブル (E1 §3.4 凍結) 内のみ
  "horizons": ["h4", 96],                        // 名前 h1/h4/h12/h24 or M15 bar 数
  "holding": {"mode": "bars | first_touch", "tp_sigma": 1.0, "sl_sigma": 1.0},
  "window": {"start": "2014-01-01", "end": "2023-12-31"}
}
```

## 組み込み規律 (構造で強制 — 運用者の注意力に依存しない)

| 規律 | 実装 |
|---|---|
| **OOS 遮断** | bars/calendar を load 直後に 2024-01-01 で物理スライス。`--unlock-oos` (S4 判定器専用、警告印字) なしにどの計算段も OOS へアクセス不能。test pin 済み |
| 診断 ≠ 判定 | レポートヘッダに禁止文言 + `verdict_authority: NONE` を自動印字 |
| 再試行禁止 | falsified 6 系統 + 価格モダリティ 3 周のチェックリストを全レポートに自動表示 |
| causal | signal は bar i close で確定 → entry は bar i+1 open。series は `lag_days>=1` 強制 |
| 再現性 | seed 固定 (20260722)、spec_hash (sha256) をレポートに印字 |
| fail-loud | silent except 禁止 — skip は全て理由付きカウント (censored/atr_nan/no_trigger/…) |

## 診断出力と「次ステージ判定の目安」

ペア×horizon 毎: **N / 摩擦調整 EV (pips) / median / WR / Spearman IC / fold 3 分割符号 / 発火頻度**。
pooled 毎に **S3 起案検討の目安** (pooled EV_fric>0 ∧ N≥60 ∧ fold 全符号一致 ∧ EV>0 ペア≥50%) を印字。
目安通過 = S3 pre-reg (候補固定 → OOS → BH-FDR) の起案検討開始であって、何の判定でもない。
uncond 系 (方向がペア内定数) は IC 定義不能 → `—` 表示、EV が診断の主役。

## 再利用資産 (再発明していないもの)

- estimand コア = `tools/event_modality_lib.py` (§3.5 SSOT: ATR14d/σ_h、first-touch **SL 優先**、NY17:00 roll daily、coverage gate 0.90、E1 §3.4 凍結摩擦、USD-leg 方向変換)
- IC 規律 = `channel_edge_ic_explore.py` と同型 (Spearman、閾値最適化禁止)
- データ = `data/cache/massive/{PAIR}_15m.parquet` 12y フル 13 ペア (**部分 parquet 罠**: ~201KB は 90d 部分版のサイン — フル版は数 MB) / イベント = `raw/bt-results/e15_e7_event_calendar.json` (FOMC 99/NFP 149/CPI 149)

## 実例 2 本 (2026-07-22 動作実証 — **診断であり判定ではない**)

| spec | 結果 (探索窓 pooled) | 読み |
|---|---|---|
| `nfp_usd_24h` (event uncond) | h4: N=813 EV **−7.4p**、h24: N=813 EV **−3.7p**、fold 不一致 | エッジなし — E15 discovery で NFP uncond 凍結候補 0 と整合。ハーネス実証用 |
| `rate_diff_breakout_template` (series ダミー × breakout、first-touch) | h4/h24: N≈4.6k EV **−3.5p** ≈ −摩擦 | ダミー (エッジ期待ゼロ) が期待どおり −friction に収束 = 配管が正しい。**実 series 接続は E20 feasibility (別 agent) の結果待ち** — column/file 差し替えだけで走る |

テスト: `tests/test_rapid_edge_probe.py` 27 件 (OOS 遮断 pin / 語彙 / causal / SL 優先 / 決定性 / 規律ヘッダ / import 副作用ゼロ、全てオフライン合成 fixture)。

## 制約・注意

- series/technical は**非重複 entry** (entry 後 max horizon 分 skip) — 発火頻度はこの規約下の値
- 語彙を増やす時は `rapid_edge_probe.py` の VOCAB_* と本 doc を同時更新 (複雑性禁止 — 小語彙が正)
- 本ツールで探索した仮説を S3 に上げる時、S2 レポートの spec_hash を pre-reg §2 に必ず転記 (探索と凍結の対応を固定)
