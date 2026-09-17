# U1 ミッション再決裁: M3 系列 (+2〜3%/月 複利) へ正式改定 — 2026-09-17

> **種別**: user 決裁記録 (rule:R1 相当 — 方針変更は user 専権、Claude は記録と KB 反映のみ自走)
> **決裁**: **U1 = (b)** ([[mission-capital-redecision-packet-2026-09-10]] §U1 の選択肢 (b) を user が 2026-09-17「推奨で進めて」で選択)
> **効力**: 即時。全施策のスコアリング分母は「time-to-M2 短縮」に統一 (監査 goals-8 の歪み解消)。
> **起点**: [[process-meta-audit-2026-09-07]] §5 U1 (実現可能性の再決裁起票) → 再決裁パケット 2026-09-10 → user 決裁 2026-09-17。

---

## 1. 決裁内容

- **正式ミッション = M3 系列: +2〜3%/月 (複利) の到達と維持**。
- 段階経路 **M1 (clean live 月次符号転換) → M2 (+0.5%/月) → M3** は 2026-07-10 段階化のまま不変。変わるのは終点: M3 が「経路の一里塚」ではなく**ミッションそのもの**になる。
- 旧 anchor **「月利21.6%接近」(user 明文化 2026-07-08) および「月利20% / 20%/月」(user 再確認 2026-08-05)** は記録から anchor 除去 — 現行ミッションの宣言、施策の正当化、優先順位スコアリングのいずれにも使用禁止。
- 判断根拠 (パケット §U1 再掲): 20%/月には ~25x レバ = unwind 即死で数学的到達経路が存在せず、橋渡し前提だった「検証済みセル在庫 年内 2-3 本」(08-05 セル・ポートフォリオ論) は全能動探索ライン FAIL で崩壊済み。M3 ですら中央シナリオ 2029+ (監査 viability-2 訂正版)。anchor として残す唯一の効果は優先順位の歪み。

## 2. 旧 anchor の disposition

| 対象 | 処置 |
|---|---|
| 「月利21.6%接近」「20%/月」を現行ミッションとして宣言する箇所 (CLAUDE.md / wiki index / roadmap v2.3 バナー / Claude auto-memory / agents/cma coordinator) | **本決裁で改定** — M3 系列宣言に置換、または superseded バナー追記 |
| 2026-07-10「aspirational anchor に格下げ」の中間状態 ([[monthly-target-rederivation-2026-07-10]] / [[shortest-path-decision-memo-2026-07-10]] D5) | **superseded** — aspirational anchor という地位も終了。導出文書は歴史記録として不改変保存 (rederivation に前方参照バナーのみ追記) |
| 歴史文書 (過去の決裁記録・監査・prereg・sessions・changelog・lessons・learning、および 21.6 が pips/WR 等の数値偶然である箇所) | **不改変** — 改竄禁止。将来これらを引用する際は「U1=(b) で除去済みの旧 anchor」と明示し、MEMORY `feedback_audit_past_verdicts_2026_08_05` (過去 verdict 監査) に従い本ページを経由する |
| user 発言の一次引用 (07-08「あなたのミッションは月利21.6%接近の達成」/ 08-05「月利20%まで持っていく」) | **保存** — 発言記録の削除は行わない。superseded マーカーのみ付す。本決裁は 08-05 指示の撤回を user 自身が 09-17 に行ったことの記録である |

## 3. 反映箇所 (本決裁と同一コミット群で改定)

- `CLAUDE.md` 最重要目標節 — 正式ミッション = M3 系列に書き換え
- `wiki/index.md` 🎯 節 — 同上 (session-start hook の head -60 注入圏内)
- `wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md` — 📌 改定バナー追記 (WS 構成は不変)
- `wiki/decisions/mission-capital-redecision-packet-2026-09-10.md` §U1 — verdict 追記
- `wiki/analyses/monthly-target-rederivation-2026-07-10.md` — superseded バナー追記 (本文不改変)
- Claude auto-memory `MEMORY.md` + `feedback_mission_monthly_21_6pct.md` (repo 外) — ミッション行の改定 + superseded バナー
- `agents/cma/coordinator.agent.yaml` — 司令塔 system prompt の 21.6% 上限記述を M3 宣言に置換 (既作成 agent は再 setup 要)
- `wiki/changelog.md` — 本決裁のエントリ追記

## 4. 残決裁 (本ページのスコープ外)

U2 (資本スケール上限の凍結) / U3 / U5 は**未決裁のまま** — パケットの既定挙動 (U2/U3 = F4 資金時計発火時に再上程、U5 = worker 課金継続) が引き続き適用される。F4 資金時計 (2026-11〜12 発火推定) は本決裁で止まらない。U4 は 2026-09-17 に推奨手順 (feasibility 比較の先行作成) を採択 — [[supply-space-feasibility-2026-09-17]] 参照、仮決めは 10-15 E1 first look / 10-18 scan#6 で。

## 5. 引用規約 (再発防止)

- 「月利21.6%」「月利20%」を含む過去文書を引用する分析は、引用前に本ページと [[monthly-target-rederivation-2026-07-10]] の estimand を確認すること (MEMORY `feedback_audit_past_verdicts_2026_08_05` 準拠)。
- 施策提案の寄与度評価は「time-to-M2 短縮」→ M3 到達確率のみを分母とする。旧 anchor 由来の期待値換算 (例: 60,244 JPY/月) の再登場は本決裁違反として lessons 起票対象。

---
決裁者: user (2026-09-17) / 記録: Claude (rule:R1、KB 反映は自走執行)
