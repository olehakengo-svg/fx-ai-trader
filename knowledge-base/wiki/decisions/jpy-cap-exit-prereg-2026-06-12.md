# Pre-registration LOCK: JPY介入キャップ・レジーム撤退条件

**作成**: 2026-06-12 (user 承認済み、roadmap v2.2 T5)
**Rule**: R1 pre-reg (発動自体は R2 で即時実行)
**状態**: 🔒 LOCKED

## 背景 (エッジのレジーム依存性)

30d LIVE 監査 (2026-06-12) で JPY 系 MR クラスタが +44.1p (USD_JPY SELL +18.4 / EUR_JPY BUY +16.5、勝ちの実質全部)。このエッジは **USD/JPY 160 介入キャップ** (財務省 ¥11.73兆 介入 4/28-5/27、「160超は介入対象」明示) が作る人工レンジ天井に構造依存する。キャップが消えればエッジの前提が消える。

## 撤退トリガー (OR 条件、いずれか成立で発動)

1. **USD_JPY D1 close > 160.80** (OANDA mid、介入帯明確突破)
2. **BOJ 利上げ実施** (政策金利引き上げの公式発表)

## 発動時アクション (機械的、裁量禁止)

- 対象戦略: `vsg_jpy_reversal` / `dt_sr_channel_reversal` / `vix_carry_unwind` / `ema200_trend_reversal`
- アクション: LIVE lot **0.5x** (SIZE lever。SKIP/停止ではない — lesson: SIZE lever > SKIP filter 2026-05-28)
- Shadow は無変更 (CLAUDE.md 原則3)
- 発動を wiki/log.md と本ページに追記

## 復帰条件

- USD_JPY が D1 close < 159.50 に回帰 **かつ** 介入観測 or 当局の 160 防衛言及が再確認された場合、lot 1.0x へ復帰 (要 KB 記録)
- BOJ 利上げ後の場合: 新レジームで 30d clean live N≥10 を再観測し、EV>0 確認後に段階復帰 (R1)

## 備考

- 本 pre-reg は「事後の裁量判断でずるずる持ち続ける」ことを排除するための事前 LOCK
- USDJPY Carry Dip v3 (`USDJPY_CARRY_DIP_LIVE_ENABLE=1`) は別系統 (押し目買い、キャップ突破はむしろ thesis 側) のため本 pre-reg の対象外。ただし BOJ 利上げ時はカラ取り前提が変わるため別途レビュー

---

## 🔴 発動記録 (2026-07-06 追記, rule:R2)

**トリガー1 成立: 2026-06-18** — USD_JPY D1 close = **161.295 > 160.80** (MASSIVE 12y cache `USD_JPY_1d_2014_2026.parquet`)。以降 2026-07-03 時点まで **14 営業日連続で 160.80 超え** (max 162.631 @06-30)、一過性ヒゲではなく明確なレジーム転換。

**執行: 2026-07-06** (検出から **18 日の執行ギャップあり** — 下記教訓参照):
- `modules/demo_trader.py` に `_resolve_jpy_cap_exit_size_lever` を実装 (LDN morning lever と同型、lot チェーン最後段・LIVE-only)。対象 4 戦略の LIVE lot **0.5x**、Shadow 無変更 (原則3)
- code pin (`JPY_CAP_EXIT_SIZE_LEVER_ACTIVE = True` 定数、env/KV 経路なし) + 回帰テスト `tests/test_t5_jpy_cap_exit_size_lever.py`。解除 = 復帰条件の KB 記録 + テスト変更を伴う PR のみ
- **Floor 1000u (pre-reg 衝突解決)**: vix_carry_unwind の Overlap pilot ([[vix-carry-grail-removal-overlap-1000u-2026-06-15]]) は「1000u 固定検証ロット」が agg-Kelly gate bypass の正当性根拠であり、500u への半減はその契約違反。より特定的な固定ロット契約を優先し、lever は `max(1000, 0.5x)` の floor 付きで適用 (1000u 検証ロットには実質 no-op、それ以上の lot にのみ半減が働く)。E2E テスト `test_vix_overlap_pilot_minlot_bypasses_gate_e2e` で契約を固定

**整合する実測** (pre-reg の予言どおりエッジ消滅):
- 2026-06-19 daily: EUR_JPY 30d +19.1→-5.3 / USD_JPY +16.3→-1.4 に反転、vix_carry_unwind +5.1→-12.6 / vsg_jpy_reversal +6.2→-18.2 と対象戦略が軒並み loser 化
- ギャップ期間 (06-18〜07-06) の対象4戦略 LIVE fill は 1 件のみ (vsg_jpy_reversal EUR_JPY 07-02, +2.2p) — 実害は限定的だったが構造は要修正

**教訓 (執行ギャップの原因)**: トリガー監視の機構が存在しなかった (コード実装なし・cron なし・手動チェックリストなし)。「決定はしたが provisioning されず、誰も気づかない」クラス (watchdog API_AUTH_TOKEN / carry dip env gate と同型)。**pre-reg LOCK には必ず監視主体 (cron or check.py) を同時に指定すること**。トリガー監視の自動化は別タスクで起案。
