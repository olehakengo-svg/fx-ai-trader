# Post-Tokyo Report: 2026-04-21

## Analyst Report
# Post-Tokyo Report — 2026-04-21 06:23 UTC（JST 15:23）

---

## 1. 東京セッション結果

**東京セッション（UTC 00:00–06:00）: トレードなし**

| 項目 | 値 |
|---|---|
| PnL | 0 pips / 0円 |
| トレード数 | 0件 |
| WR | N/A |

全17モード中、Runningは11モード稼働中だが、東京セッション通じてエントリーゼロ。

---

## 2. What Worked

**該当なし** — エントリーが一件も発生していないため成功事例なし。

---

## 3. What Didn't Work

**該当なし（直接的な失敗トレードなし）**

ただし、ブロック統計が間接的な「機能不全」を示している：

| ブロック要因 | 件数 | 主ボトルネック |
|---|---|---|
| `rnb_usdjpy:direction_filter` | 188 | USD_JPYがRANGINGレジーム → 方向性フィルターが全拒否 |
| `daytrade_eurjpy:score_gate` | 182 | EUR_JPYはTRENDING_UPだが採点閾値超えられず |
| `daytrade_gbpusd:score_gate` | 172 | GBP_USDはRANGING → スコア低下で通過できず |
| `scalp_eur:session_pair` | 152 | セッション制限による排除（東京時間はEURペア不可） |
| `daytrade_gbpjpy:score_gate` | 148 | GBP_JPYはRANGING → 同上 |
| `daytrade_eurgbp:gbp_asia_flash_crash` | 61 | アジア時間のGBP急変動ガード発動 |
| `scalp:spread_guard` | 35 | スプレッド拡大によるスキャルプ抑制 |

**構造的観察**: ブロックの主因は「方向性なき相場」＋「セッション制限」の複合。システムは想定通りに機能しており、問題はシグナル不足ではなく市場環境そのもの。

---

## 4. 戦略調整判断

**→ NO（パラメータ変更不要）**

根拠：
- Fidelity Cutoff後のクリーンN=0（本日東京）であり、統計的判断材料が存在しない
- ブロック理由は全てレジーム・セッション・スプレッドに起因しており、パラメータ誤設定の証拠なし
- `direction_filter`（188件）は USD_JPY RANGING環境での正常動作
- `score_gate`系の多発は、複数RANGINGペアに対する適切な保守動作と解釈できる
- DD=25.9%でDD防御0.2x発動中 → 現状でのパラメータ緩和は禁忌

---

## 5. ロンドンセッション準備（UTC 07:00–）

### ATR/レジーム変化予測

| ペア | 現在レジーム | ロンドン移行後の予測変化 |
|---|---|---|
| EUR_USD | TRENDING_UP / ATR 52%ile | ロンドンオープン時の方向継続バイアス高。ATRさらに上昇の可能性 |
| EUR_JPY | TRENDING_UP / ATR 38%ile | モメンタム継続圏。スコアゲート通過機会が増える可能性 |
| GBP_USD | RANGING / ATR 57%ile | 高ATRにも関わらずRANGING → ブレイクアウト注意。方向感出れば急騰 |
| GBP_JPY | RANGING / ATR 36%ile | 低ATRのRANGING → スキャルプ有利だがブロック継続の可能性 |
| USD_JPY | RANGING / ATR 41%ile | `rnb_usdjpy:direction_filter`の継続ブロックが濃厚 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 理由 |
|---|---|---|---|
| ◎ 最優先 | `daytrade_eurjpy` | EUR_JPY | TRENDING_UP×score_gate解除期待。ロンドン開始でスコア上昇見込み |
| ◎ 最優先 | `daytrade_eur` / `scalp_eur` | EUR_USD | TRENDING_UP×ATR中位 → DT・スキャルプ両対応 |
| ○ 注目 | `scalp_5m_gbp` / `scalp_5m` | GBP_USD | RANGINGだが高ATR → 小幅レンジ内スキャルプは有効 |
| △ 様子見 | `daytrade_gbpusd` | GBP_USD | score_gate抑制中。RANGING解消まで低期待 |
| ✕ 期待薄 | `rnb_usdjpy` | USD_JPY | direction_filter 188件 → ロンドン時間も同様に全拒否の可能性大 |

### セッション移行での注意点
- **`gbp_asia_flash_crash`ガード（61件）**: ロンドンオープン直後はGBPボラティリティ急増リスクあり。`daytrade_eurgbp`は最初の15分は慎重に扱われる可能性
- **OANDA Live Rate = 0%**: 全50トレードがSKIP状態。本番資金への転送ゼロは shadow_tracking継続を意味する。ロンドンセッションでN蓄積が進まない限り、この状態は継続

---

## 6. クオンツ見解

### 最重要シグナル

**「システムは正しく動いているが、市場が東京時間に協力しなかった」という整理が正確。**

ブロック総数 **1,416件超**に対してエントリーゼロ、かつ全50件がOANDA SKIP（shadow_tracking）という状態は、DD=25.9%の防御モードとRANGINGレジームの複合圧力下での完全なエントリー自制を示す。これはバグではなく設計通り。

**今日の構造的懸念点は1点に絞られる：**

> **OANDA Live Rate 0%が継続している** — Cutoff後クリーンNが全戦略でほぼ未蓄積であり、N≥30の昇格基準到達が見えない。ロンドン・NYセッションでエントリーが発生しなければ、今週中のKelly Half移行シナリオは機械的に遠のく。

ロンドンセッションでEUR_USD・EUR_JPYのTRENDING_UP環境でscore_gateが解除されるかどうかが、**今日の最重要観察点**である。
