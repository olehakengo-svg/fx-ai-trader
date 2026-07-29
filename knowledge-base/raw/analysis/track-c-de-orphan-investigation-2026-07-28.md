# Track C D-e 実装前調査 — orphan fills 出所特定 (2026-07-28)

**調査者**: 独立 analyst subagent。**結論: orphan 28 件は 2 バケットに分割され、パケットの
「30000u = preserve 系」仮説は反証された。**

## バケット 1: 30000u × USD_JPY × 7 件 (07-10/13) = **手動 / 外部クライアント**

| oanda_id | dir | units | open (UTC) | 保有 | TP/SL | PL (JPY) |
|---|---|---|---|---|---|---|
| 549111 | BUY | 30000 | 07-10 16:31:40 | 601s | なし | +1,350 |
| 549115 | SELL | 30000 | 07-13 02:15:37 | 7s | なし | −180 |
| 549119 | BUY | 30000 | 07-13 02:15:57 | 603s | なし | −60 |
| 549123 | BUY | 30000 | 07-13 02:48:42 | 600s | TP+49.6p/SL−10.3p | +810 |
| 549131 | BUY | 30000 | 07-13 06:54:06 | 601s | なし | +180 |
| 549135 | BUY | 30000 | 07-13 09:15:24 | 608s | TP+48.8p/SL−11.3p | −1,080 |
| 549143 | BUY | 30000 | 07-13 10:31:43 | 602s | TP+50.0p/SL−10.0p | −600 |

小計 +420 JPY。**非システムの根拠 (4 点)**: (1) bridge 監査 13,532 行 (悉皆) に 7 件の
oanda_trade_id が 0 行、(2) SL/TP なし成行はコード上生成不能 (oanda_bridge.py:632-638 は常時
SL/TP 付与)、(3) リテラル 30000u の lot 導出経路がコード全体に不在、(4) 600±8 秒 time-exit は
どの exit にも該当せず、SELL→7 秒 close→13 秒後 BUY 反転は人間の方向訂正パターン。
発生は JST 月曜日中。clientExtensions なし。

**→ ✅ 解決 (2026-07-29 user 確認)**: **本人の手動発注と確認** — トークン漏洩ではない。
運用ポリシー: 手動 fill は戦略 EV/台帳統計から除外 (estimand 汚染防止)、NAV 影響としては
unattributed バケットで可視化。**推奨 (未決)**: システム口座 (Claude_auto_trade_KG) と手動取引の
サブアカウント分離 — 分離しない場合、手動約定は今後も orphan として現れ、日次 reconcile 導入まで
equity ガードの死角に残る。

## バケット 2: 残り 21 件 (+ 04-09/10 の 12 件) = **PYR child の構造的台帳欠落**

- 全件 audit 上 `filled` + demo_trade_id = `PYR_*` (pyramid child synthetic ID)
- `demo_trader.py` (旧 2894-2980): PYR child は `open_trade(demo_trade_id=_pyr_id)` を呼ぶが
  **demo 台帳への行作成なし・fill callback なし** = 設計上 link され得ない構造ギャップ
- 生涯実績: **N=33 fill / WR 9.5% / net −5,212 JPY**、同一親 6 連 fill (in-memory dedup 不全 —
  「engine 毎 tick 再構築 = dedup 死」既知欠陥の再現)。全件 10000u、保有 1〜171 秒
- 会計恒等式: 40 orphan (28 D-a + 12 早期) = net −6,821.1 JPY、D-a の 28 件 −4,792.0 と
  小数第 1 位まで一致 (= 監査インフラ自体は信頼できる)

**→ 執行済み (R2、2026-07-28)**: `_PYRAMIDING_CODE_PIN_DISABLED = True` code pin (不可逆)。
根拠 = N=33 / WR 9.5% / 台帳外 / dedup 不全の 4 点で R2 降格基準充足。env kill switch は
pin にならない (watchdog DECREMENT 教訓)。再武装は R1 + child の demo 台帳行実装 +
dedup 永続化が pre-reg 必須。

## equity ガード設計への含意

- **母集団定義の向きの訂正**: 「demo 起点 join」は join key のない fill (PYR/手動) を両方落とす。
  正しくは「broker 全 fill 起点 → demo へ left join → unmatched を unattributed 警報」
- 日次 reconcile (broker fill vs 台帳 link) の常設監視が必要 — 今回の 28 件は 3.5 ヶ月不可視だった
- 手動 fill は戦略 EV/台帳統計から除外 (estimand 汚染)、ただし NAV 毀損としては可視化必須
