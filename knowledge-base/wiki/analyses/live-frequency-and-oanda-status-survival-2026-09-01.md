# Live 頻度崩落の構造分解 + OANDA ステータス = API 存続問題 (2026-09-01)

**起点**: user 指摘「トレードの頻度少なすぎ」「lot・頻度が少なく自動売買の仕組みを維持できなくなる」+ OANDA 会員ステータス画面 (現在 PLATINUM / 来月 SILVER / 今月取引額 $0)。

## Part 1: OANDA ステータス = API 存続条件 (最優先・期日 2026-09 月内)

### 事実 (一次ソース確認済み)
- **REST API 利用条件 = 「会員ステータスが Gold の方でプロコースかつ口座残高が 25 万以上」+「API をご利用いただいている間は、この条件を継続して満たす必要があります」** ([FAQ 720](https://help.oanda.jp/oanda/faq/show/720), [platform/api](https://www.oanda.jp/platform/api))
- 条件割れ → API 利用停止。復帰は「再度条件を満たしていただければ…**その際にはトークンの再発行が必要**」([FAQ 1730](https://help.oanda.jp/oanda/faq/show/1730)) = 既存トークン無効化
- ステータス閾値 ([lab-education/status](https://www.oanda.jp/lab-education/status/)): GOLD = 前月取引量 **USD 50 万以上**。取引量は**新規+決済の双方**でカウント (25 万通貨買い + 25 万通貨決済 = 50 万ドル)。毎営業日判定、アップグレードは翌月末まで維持
- スクリーンショット (2026-09-01 15:02 JST): 現在 PLATINUM (9 月末まで有効) / **来月 = SILVER** (8 月出来高不足で確定見込み) / 今月取引額 $0 / 「今月の取引量が 500,000 ドルを越えると来月から GOLD に昇格」

### 帰結
**9 月中に取引量 $500k を積まなければ、10 月に SILVER 降格 → REST API 停止 = 自動売買・データ収集の物理停止。**

blast radius (コード実測):
- live 執行: 全停止 (OandaBridge)
- **E1 positioning ingest (OANDA v3 order book / position book): 停止** — E1 は現在唯一の能動供給ライン、first look 2026-10-15 の直前に観測穴が開く
- OANDA テレメトリ (heartbeat / NAV / transaction audit / 549250 型監査): 停止
- 価格フィード: OANDA primary → **Massive → yfinance fallback で shadow 蓄積は劣化継続** (modules/data.py の 3 段構成)
- 復帰時: トークン再発行 + Render env 差し替え + GOLD 復帰まで最短 1 ヶ月 (翌月適用)

### 出来高の現実
| ソース | 月間出来高 (新規+決済) | 対 $500k |
|---|---|---|
| 8 月実績 (LIVE 14 件 × 1000u 固定) | ≈ **$28k** | 5.6% |
| 有機レバー全部引いた楽観シナリオ (41-53 件/月 × 1000u) | ≈ $82-106k | 16-21% |
| 必要 | **$500k/月 (毎月)** | — |

**→ MIN lot 規律 (1000u 契約) の下で、エッジトレードだけでは構造的に GOLD を維持できない。** lot ladder は凍結テンプレ (昇格 = 段ごと R1) であり、ステータスのために lot を上げるのは規律違反。

### 対応オプション (user 決裁事項)
| 案 | 内容 | 月間コスト | リスク | 備考 |
|---|---|---|---|---|
| **A: status volume keeper (自動)** | 専用モジュールが USD_JPY 10,000u の即時往復 (数秒保有) を ~25 回/月 (≈1.2 回/営業日、東京流動時間帯) 実行 | spread 0.3-0.8 銭 × ¥100/pip ≈ **¥1,000-3,000 + slippage** | 保有数秒 × 10k units (1p 逆行 = ¥100)。スプレッド異常時 skip (動的デスゾーン準拠) | margin ¥64k/RT (25x)。**50,000u 単発は margin ¥320k > NAV で不可能** → 小口 × 多数が唯一解。要 design: 専用 entry_type + Kelly/agg-Kelly 母集団・quant-eval・**freshness 検知器**・T5 cap・cascade から除外 (読み手除外を同一コミットで) |
| **B: user 手動出来高** | 月 1 回 10-50 万通貨往復を手動で数回 (7 月の 30k×7 と同型) | 同等 (spread) | 手動ミス、毎月の作業負荷 | コード変更ゼロ、データ汚染ゼロ |
| **C: 見送り (SILVER 受容)** | — | ¥0 | **API 停止 = プロジェクトの live/E1/テレメトリ停止**。M1 進行不能 | ミッション (M1→M2→M3) と非整合 |

**期日**: 取引量反映は「取引日の翌日 17 時以降、数日かかる場合も」→ **09-24 頃までに $500k 完了が安全**。
**併設リスク**: NAV ¥278,345 vs 残高床 ¥250,000 = **バッファ ¥28k**。API 存続のもう 1 つの条件。NAV < ¥260k で Discord 警報を出す watchdog 追加を推奨 (R3・安価)。

## Part 2: live 頻度崩落の構造分解 (Workflow 4 系統監査、2026-09-01)

### 月次 LIVE 件数 (API 実測、oanda_trade_id != '')
**6 月 92 → 7 月 28 → 8 月 13 → 9 月 0** (全行は 3,436 / 3,252 / 1,820 行 = shadow 供給は健在)

崩落は市場でなく構造: ① 07-02 P1 fix で agg-Kelly gate 初実効化 ② 07-10 固定 cutoff 決裁で恒久負 ③ 08-03 vix R2 demote → **8 月以降の live 経路 = min-lot bypass 9 セルのみ** (carry_dip×1 + price_shock_rev×5 + weekend_gap_fade×3、全て 1000u 固定契約)。

### Aggregate Kelly gate の現在構造
- gate 値 **-0.315〜-0.374 で恒久負** (母集団 = 固定 cutoff 2026-04-16 以降の clean live 累積、4-7 月の負エッジ史が恒久的に分母)
- 対照: rolling 30d Kelly は **+0.256** (N=13, +94.3p) — 「直近 clean live は正なのに gate は過去累積で閉鎖」が現状
- 直近 14 日 (ログ retention 窓) で blocked 41 件 vs BYPASS 4 件。blocked 上位: xs_momentum_rsi 18 / donchian_momentum 7 / **kalman_d7_po_dn_flip 6**
- PAIR_PROMOTED 12 セルは「live 資格あり・agg-Kelly で全滅」= 現体制で live 到達ゼロ

### kalman_d7 の整合性問題 (最重要発見)
- user は 2026-05-28 に kalman live 化を決裁済み (**SUCCESS 定義 = OANDA fill ≥1**)。08-09 PR #168 で経路開通
- しかし kalman は `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` 非メンバー + FLAT 5000u > bypass 上限 1000u の**二重不適格で構造的に live 不能** — 決裁から 96 日、live N=0
- gate 衝突は設計時 (08-09) 未認識、初認識 = 本セッション
- 退避 registry `t9-kalman-d7-live-n10-ev-check` は「LIVE N≥10 で判定」— **分子が発生不能な registry** (2026-11-30 stale 確定コース)
- shadow 実績: 90d 12 行 (~19 件/月ペース)、9W/2L +13.5p (N 極小・観測値)

### M1 検出力 (8 月実測 σ=23.7p ex-549250 / 41.6p テール込み)
| 想定エッジ | 必要 N (80%pw, one-sided 5%) | 現行 14/月での所要 |
|---|---|---|
| +3p/trade | 385 | 27.5 ヶ月 |
| +2p/trade | 865 | 62 ヶ月 |
- 現行 14/月の検出可能最小エッジ = **15.7-27.7p/trade** (非現実)。真のエッジ +3p でも月次符号が正に出る確率 60-68% = **M1 は現頻度では統計判定不能**
- 8 月 live: 549250 込み −28.9p / 除外 +94.3p — 月次符号が 1 トレードで反転する分散

### 頻度レバー (ΔN/月、決裁状態)
| レバー | ΔN/月 | 決裁状態 | 備考 |
|---|---|---|---|
| carry_dip レジーム復帰 (USD/JPY<159.5) | +12-13 | 不要 (待つだけ) | 現値 159.8。レジーム依存で消失もあり得る |
| **kalman carve-out (1000u 化 + bypass set 追加)** | +11-17 | **R1 + user 決裁** (D4 準拠 pre-reg) | 5000u FLAT のままでは N 増ゼロでリスク 5×。1000u 化とセットが合理的。テール ¥3,700/月 (全敗仮定) |
| P-S1(a) sweep 執行 | +1-3.5 | **完了 (N=9/10 待ち)** | 成立日に機械執行、bypass メンバーなので実 fill が出る |
| carry_dip H13/H16-20 静的窓免除 | +3 | R1 (前例 = sweep gbp_asia パケット形式) | エビデンス N=3-4 で薄い。較正母体は 2026-04 の旧ブック N≤27・再較正なし |
| carry_dip ceiling 160.5 (探索的) | +2-3 | R1 案 B (外部一次情報必須、PnL 選定禁止) | 161.5 は 160.5 と無差別 (期間 max close 160.195)。設計思想 (壁回避) と正面衝突 |
| Bonf PASS セル ②③④ 昇格 | 未定 | R1 未起票 | ①sr_anti_hunt は NO-GO 済み。②donchian×NZD_USD の D-c-2 再審 (shadow N≥50) は registry 未登録 = 機械監視外 |
| R2 demote 13 セル復帰 | **0** | — | demote 前から live 寄与ゼロ (shadow emission のみ) |

合算: 現状 14/月 → 保守 41/月 → 楽観 53/月。M1 必要 N=385 到達は最速 **7.3-9.4 ヶ月** (現状 27.5 ヶ月)。

### 教訓 (新規)
- **「live 化を決裁した」と「送信が発生しうる」は別物** — kalman は決裁済み・env 有効・経路開通の三拍子が揃って 96 日間 fill ゼロ。live 化決裁時は必ず「OANDA 送信 gate chain の最後まで」の到達性を確認し、fill 発生を registry で監視する (ZN 型到達性欠陥の live 送信版)
- **ブローカーの口座条件 (ステータス/残高) はシステムの存続変数** — エッジとは独立に監視・維持対象。取引量・残高・ステータスを watchdog に載せる

## 未決 (user 決裁待ち)
1. **9 月の $500k 対応**: 案 A (keeper 自動) / 案 B (手動) / 案 C (見送り)
2. kalman carve-out R1 パケット起草の GO (起草自体は分析作業として着手可)
3. NAV 残高床バッファ (¥28k) の扱い
