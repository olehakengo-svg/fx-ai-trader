# Post-London Report: 2026-05-07

## Analyst Report
# ロンドンセッション総括レポート（UTC 07:00–16:00）
**生成日時: 2026-05-07 17:42 UTC / JST 05-08 02:42**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数 | 11件 |
| 勝率 | 63.6%（7勝4敗） |
| PnL | **-10.0 pips** |
| 平均勝ちトレード | +2.3 pips |
| 平均負けトレード | -7.8 pips |

**サマリー**: WR63.6%にもかかわらずPnLはマイナス。ペイオフ比（勝ち平均/負け平均）= 0.30という深刻な非対称性が支配している。「多く勝って大きく負ける」典型的なリバーション系の病理。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **trendline_sweep** | GBP_USD | **+3.9 pips**（3戦全勝） | GBP/USDがTRENDING_UPレジーム（ATR%ile 41%、SMA slope +0.0055）にあり、上方トレンドラインのブレイクが機能。低ATRでのトレンドフォローが一致。 |
| **vix_carry_unwind** | USD_JPY | **+0.8 pips** | USD/JPYのVOLATILEレジーム（ATR%ile 78%）でキャリー巻き戻しのSELL方向（SMA slope -0.0037）が相場と整合。 |

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **wick_imbalance_reversion** | GBP_USD | **-9.3 pips（1発）** | TRENDING_UPレジームでリバーション系を打った構造的ミスマッチ。トレンド相場で逆張りエントリーがSL直撃。 |
| **bb_rsi_reversion** | USD_JPY | **-4.8 pips**（2戦1勝1敗） | 負けトレード単独で-8.5 pips。VOLATILEレジームでBBリバーションのSLが広すぎ、一方向に突き抜けた。 |
| **bb_rsi_reversion** | GBP_USD | **-0.6 pips**（4戦2勝2敗） | TRENDING_UPに逆らうリバーション。勝ち負けが相殺されるがEV=-0.15と微妙にマイナス。 |

---

## 4. 東京との比較

| 指標 | 東京（推定） | ロンドン |
|---|---|---|
| 本日累計N | 15件 | うち11件 = 東京4件 |
| 本日累計PnL | -46.0 pips | ロンドン分: -10.0 pips |
| 東京分PnL推定 | **-36.0 pips** | — |
| 累計WR | 53.3% | ロンドン: 63.6% |

> **東京セッション推定PnL: -36.0 pips / 4件**

東京の4件で-36 pipsという異常な損失密度（-9 pips/トレード平均）。日足累計の大半は東京時間に発生。**daily_loss_limit（-35.1pips <= -20.0pips）でOANDAブリッジが本日すでにブロック状態**であり、東京時間の損失がリミットを超過している。ロンドンはWR改善・損失縮小と相対的に良好だったが、日次リミット達成後の稼働。

---

## 5. NYセッション準備

### レジーム予測（UTC 16:00–21:00）

| ペア | 現在レジーム | NY移行予測 | 根拠 |
|---|---|---|---|
| USD_JPY | VOLATILE(78%) | 引き続きVOLATILE | 米経済指標・FED関連でさらにボラ拡大リスク |
| GBP_USD | TRENDING_UP(41%) | 方向感維持 or 利益確定調整 | ロンドンクローズで一時的フラッタリング |
| EUR_USD | RANGING(43%) | RANGING継続 | 低ATR%ile、NY指標なければ変化小 |
| EUR_JPY / GBP_JPY | VOLATILE | VOLATILE維持 | JPY全体の不安定さが継続 |

### 推奨戦略配分

| 推奨度 | 戦略 | ペア | 理由 |
|---|---|---|---|
| ◎ **継続** | trendline_sweep | GBP_USD | 本日唯一プラスEV実績。TRENDING_UPレジームと一致。ELITE_LIVE戦略 |
| ○ **条件付き** | vix_carry_unwind | USD_JPY | VOLATILEレジームで機能。ただしN=1（本日）、USD方向性次第 |
| △ **様子見** | bb_rsi_reversion | GBP_USD | TRENDING_UPでリバーションは構造的不利。本日EV=-0.15 |
| ✕ **NO ACTION推奨** | wick_imbalance_reversion | GBP_USD | -9.3pips/1発。TRENDING_UPでリバーション系は構造的禁忌 |
| ✕ **NO ACTION推奨** | bb_rsi_reversion | USD_JPY | VOLATILE相場でSLが広く、-8.5pips級の損失リスク継続 |

### ⚠️ 重大制約事項

> **daily_loss_limit（-35.1pips）は本日東京時間に既に超過・OANDA本番ブロック発動済み。**
> NYセッションはデモ稼働のみ。OANDA本番転送は本日中に再開しない。
> 実質的に「NYセッション = データ収集モード」として位置づけるべき。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計トレード数 | 15件 |
| 累計WR | 53.3%（8勝7敗） |
| 累計PnL | **-46.0 pips** |
| OANDA転送率 | 10%（5/50件） |
| 本日OANDA本番稼働状態 | **ブロック中**（daily_loss_limit超過） |
| NAV | 435,313.6036 |
| DD水準 | 28.01%（DD防御モード） |

---

## クオンツ見解

### 🚨 最重要シグナル

**「ペイオフ比0.30」という構造破綻がWRを無効化している**

本日11件でWR63.6%を達成しながらPnL=-10 pips。平均負けが平均勝ちの3.4倍という非対称性は、ロンドンセッション単独の問題ではない。東京含む本日累計でも同様の構造（WR53%でPnL=-46 pips）。**「リバーション系戦略がトレンド相場（GBP/USD TRENDING_UP、JPY系VOLATILE）で稼働している」**という根本的なレジームミスマッチが原因。

trendline_sweep（ELITE_LIVE）が唯一GBP/USDのTRENDING_UPレジームに適合して+3.9 pipsを出した事実が、残りの戦略との対比を際立たせている。

**NYセッション判断**: daily_loss_limitによりOANDA本番は本日ブロック済み。デモ収集データとしてtrendline_sweepのGBP/USD パフォーマンスを蓄積しつつ、wick_imbalance_reversionとbb_rsi_reversion USD_JPYはレジーム整合性の観点から**本番昇格基準（EV≥1.0）に到達する構造にない**と判断する。N蓄積よりもレジーム適合性の審査を先行させることを推奨する。
