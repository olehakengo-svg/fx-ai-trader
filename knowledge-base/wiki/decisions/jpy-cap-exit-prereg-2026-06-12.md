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
