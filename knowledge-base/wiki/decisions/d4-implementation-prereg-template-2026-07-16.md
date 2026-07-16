# D4 実装 pre-reg テンプレート — survivor 到達時に即起案するための雛形 (2026-07-16)

> **目的 (最短経路)**: 供給ライン (E1 等) から survivor が出た瞬間、実装 pre-reg の起案が
> ゼロからの設計にならないよう、D4 必須 4 項目 + 防御解除ラダーの構造を事前に固定しておく。
> survivor 到達時はセル固有の数値 (N/EV/Wilson/摩擦/lot) を埋めるだけにする。
> 本テンプレート自体は R3 (文書のみ、live 変更なし)。個別起案は R1 + user 承認 (D3 SLA 48h)。

## 埋めるべきセル固有値 (起案時)
- セル: `{entry_type} × {instrument} × {direction}`
- 根拠 pre-reg verdict: {{verdict pre-reg ドキュメントへのリンクを起案時に記入}} §8 (PASS 数値: EV/p/BH-q/N)
- 摩擦: per-pair RT friction (KB friction table) / 摩擦調整後 EV
- shadow 発火実測レート (件/月) → live N≥30 到達見込み日

## (i) agg-Kelly gate per-cell carve-out 設計
- 経路は 2 択を事前固定: (a) `edge_cell_force_live` (既存コード経路) / (b) minlot bypass 契約準拠 (≤1000u, frozenset 追記)
- 選定規準: 初回 pilot は **(b) minlot 1000u** を既定とする (実弾最小・契約型・監視レール既存)。
  (a) force_live は lot chain が絡むため第 2 段以降でのみ検討
- carve-out は **セル単位** (pool 禁止 — M6 ゲートと矛盾するため。決裁メモ 2026-07-10 で棄却済み)

## (ii) R2 自動降格ゲート併設 (bypass 機構の必須対、教訓: watchdog DECREMENT)
- 降格条件を数値で事前固定: 例 live N≥10 で EV < −(摩擦×1.5) or 連続 5 敗 or DD 寄与 > Xp
- 降格の実効機構は **code pin** (KV disable は pin にならない — 教訓)
- watchdog / registry のどちらが監視主体かを明記 (pre-reg には監視主体を必ず併設 — T5 教訓)

## (iii) 判定はセル単位
- promote/demote 判定に使う集計は `oanda_trade_id != ''` (TRUE_LIVE) のセル単独集計のみ
- pool 判定は口座レベル判断専用 (M6 には使わない)

## (iv) shadow parity 検証
- live pilot 開始前: shadow 発火 vs BT 前提の fill/spread/slippage 突合 (最低 N=10)
- E1 系セルの場合は追加で **データ再現性 spot check** (Myfxbook 再取得値 vs 保存値) — TV Pine canon の非価格版

## 防御解除ラダー (決裁メモで方向固定済み、数値は起案時に確定)
- 0.2x 据置 → 段1: minlot 1000u carve-out (本 pre-reg) → 段2: 5000u (セル単位 live N≥30 ∧ Wilson 下限 EV>0)
- 各段に R2 復帰条件 (上記 (ii) と同一機構) を対で定義
- 「clean live 30d EV>0」単独をトリガーにしない (N≈17/30d ではノイズ — 決裁メモで棄却済み)
