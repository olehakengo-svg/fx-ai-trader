# Post-London Report: 2026-06-29

## Analyst Report
# ロンドンセッション Post-London Report (JST 03:00 / UTC 18:03)

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数（N） | 8 |
| 勝率（WR） | 87.5% (7W/1L) |
| 総PnL | **+3.3 pips** |
| 平均EV/トレード | +0.41 pips |

> ⚠️ WRは優秀（87.5%）だが、**単一LOSS（-8.5 pips）が7勝の+11.8 pipsを食いつぶし**、セッション利益を圧縮。リスク非対称性に注意。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **vsg_jpy_reversal** | EUR/JPY | +2.2 pips | EUR/JPYのRANGINGレジーム×SL_HITによる迅速利確で逆張りが機能 |
| **dt_sr_channel_reversal** | EUR/JPY | +2.1 pips | SRチャンネル内での反転を正確に捉え、RANGING相場と親和性高 |
| **wick_imbalance_reversion** | GBP/USD | +2.0 pips | GBP/USDのRANGINGレジームでウィック反転が素直に機能 |
| **trendline_sweep** | GBP/USD | +1.3 pips | RANGING×SMA下降傾向でスウィープ後の戻りを捕捉 |
| **zz_pivot_v60_sr**（3勝分） | EUR/USD | +4.2 pips | SELL方向がTRENDING_DOWN（SMA20=-0.0056）と整合、3勝を積み上げ |

**共通成功パターン**: RANGING通貨ペア（EUR/JPY・GBP/USD）での逆張り系戦略が一致して機能。レジームとの親和性が高い。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **zz_pivot_v60_sr** | EUR/USD | -8.5 pips | TRENDING_DOWN中でピボット逆張りを仕掛けSL直撃——EUR/USDのATR%ile 69%の高ボラ局面でSLが近すぎた可能性 |

**EVの矛盾**: セッション内のzz_pivot_v60_srはN=4でEV=-1.07だが、同戦略が3勝しながら単一の-8.5 pips LOSSで全体EVを引き下げる「逆サイズ問題」が見える。TP/SL非対称がセッション単位で顕在化。

---

## 4. 東京セッションとの比較

> ※東京セッションデータが本データセットに明示されていないため、本日累計（N=9, WR=88.9%, PnL=+5.4）とセッション内（N=8, WR=87.5%, PnL=+3.3）の差分から推定。

| 指標 | 東京（推定） | ロンドン | 評価 |
|---|---|---|---|
| N | 1 | 8 | ロンドンで活発化 |
| WR | 100.0% | 87.5% | 若干低下（LOSSが発生） |
| PnL | +2.1 pips | +3.3 pips | ロンドンで利益増加 |
| 主レジーム | — | RANGING優位 | 逆張り系が有効な地合い |

東京1件（PnL=+2.1、WR=100%）からロンドンで8件に増加。絶対利益はロンドンが上回るが、LOSSの初発生によりリスクも顕在化。**ロンドン時間のボラ上昇（ATR%ile 60-69%）が両方向に作用**した典型セッション。

---

## 5. NYセッション準備（UTC 13:00–21:00 / JST 22:00–翌06:00）

### ATR/レジーム変化予測

| ペア | 現レジーム | NY移行予測 | 根拠 |
|---|---|---|---|
| EUR/USD | TRENDING_DOWN | **継続〜加速** | SMA20=-0.0056と最大傾斜、ATR%ile 69%——NYオープンで一方向性リスク高 |
| GBP/USD | RANGING | **RANGING維持〜やや拡大** | ATR%ile 60%で中程度、SMA若干下向き——NY初動の方向感次第 |
| EUR/JPY | RANGING | **RANGING維持** | SMA20=-0.00177とほぼフラット、53-62%ATRで安定圏 |
| GBP/JPY | RANGING | **RANGING継続** | ATR%ile 67%だがSMAフラット、円相場はUSD/JPYに連動 |
| USD/JPY | RANGING | **要警戒** | SMA=+0.00382と上昇傾向——NY雇用・PMI系指標で急変リスク |

### 推奨戦略配分

**✅ ACTIVE推奨**

| 戦略 | ペア | 理由 |
|---|---|---|
| vsg_jpy_reversal | EUR/JPY | RANGINGと逆張りの親和性をロンドンで実証済み |
| dt_sr_channel_reversal | EUR/JPY | 同上、SRチャンネル有効性確認済み |
| wick_imbalance_reversion | GBP/USD | RANGING継続想定で機能継続が見込まれる |

**⚠️ 要注意（条件付き）**

| 戦略 | ペア | 条件 |
|---|---|---|
| zz_pivot_v60_sr | EUR/USD | **TRENDING_DOWN継続中はピボット逆張り回避**——SELL方向限定でも-8.5 pips LOSSのリスク継続 |
| trendline_sweep | GBP/USD | NYオープン初動の方向感確認後に判断 |

**🚫 NO ACTION推奨**

- **EUR/USDへの逆張り系戦略全般**: ATR%ile 69% × TRENDING_DOWN × SMA=-0.0056 の組み合わせはピボット/SR逆張りの天敵。NYで更に加速するリスク。
- **新規ポジション積み増し全般（USD/JPY関連）**: NYセッション序盤に経済指標警戒モードが必要。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計N | 9 |
| 累計WR | 88.9% |
| 累計PnL | **+5.4 pips** |
| OANDA転送率 | 18%（50件中9件LIVE） |
| 実効NAV | 283,583.98 |

> OANDA転送率18%は引き続き低水準。shadow_trackingブロック20件が主因で、Sentinel N蓄積フェーズ中であることを示す。

---

## 7. クオンツ見解

### 🔴 最重要シグナル

**zz_pivot_v60_sr の非対称ペイオフ問題が本日顕在化**。
同戦略はセッション内WR=75%（3勝1敗）ながらEV=-1.07——これはLOSS時の-8.5 pipsがWIN時の平均+1.4 pipsの**約6倍**であることを意味する。TRENDING_DOWN環境でのピボット逆張りは「多く勝って大きく負ける」構造的な非対称リスクを内包している。EUR/USDがTRENDING_DOWN継続中である限り、この戦略の期待値は構造的にマイナス方向へのバイアスを受け続ける。

**推奨判断**: zz_pivot_v60_srのEUR/USD運用はレジームがRANGINGへ転換するまで監視継続。NY追加LOSSが出た場合は即座に降格検討ラインとして認識すべき（現時点N=4で判断早計だが、方向性は明確）。

### 🟡 構造的観察

- **OANDA転送率18%はシステム正常動作の証拠**（shadow_tracking主因
