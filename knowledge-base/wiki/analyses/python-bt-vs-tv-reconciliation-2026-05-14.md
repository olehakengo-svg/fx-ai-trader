# Python BT vs TV BT — 整合チェック (xs_momentum × USDJPY 15m)

**Date**: 2026-05-14
**Rule**: R3 (Immediate — 整合の有無は math invariant、ただし基準数字の古さに注意)
**Status**: 構造差分マップ確定 / 最新 Python BT (2026-05-05) で再評価完了 / 古い KB 数字 (2026-04-14) を deprecate
**Source**: `strategies/daytrade/xs_momentum.py`, `app.py:6231-7000`, `bt-results/tv-overlays/xs_momentum-replica.pine`, `knowledge-base/raw/bt-results/xs_momentum-shadow-bt-2026-05-05.json`

## ⚠️ 最初の発見: KB の「Python BT 真値」が古い

整合チェックを始める時点で参照していた KB 数字は **1 ヶ月前 (2026-04-14)** の comprehensive scan 由来:
- 旧 KB 引用: `N=342, WR=69%, EV=+0.270, PF=1.43` (出典: `raw/bt-results/comprehensive-bt-scan-2026-04-14.md`)
- 最新 (2026-05-05 365d shadow BT): **`N=608, WR=60.4%, EV=-0.007, PF=0.99, PnL=-4.0`** ← **break-even / -EV**

**教訓**: 「定量評価の最初のステップは changelog.md を読んで date_from を決める」を踏まなかった。古い数字を真値として整合チェックを始めると、25pp gap → 構造差分仮説の組み立て自体が虚像になる。今回は途中で artifact 直読で気付いた。

## 比較対象の更新

| Side | Period | Friction | Co-strategies | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|---|---|---|
| **Python BT shadow** (`xs_momentum-shadow-bt-2026-05-05.json`, 365d, isolated) | 2025-05-05〜2026-05-05 | 2.14 pip RT | 単独 | **608** | **60.4%** | **-0.007** | **0.99** | **-4.0** |
| **Python BT 318d full** (`/tmp/xs_mom_bt_318d.json`, 2026-05-14 実行) | ~318d (lookback=318) | 2.14 pip RT | **全 20 戦略同時** | **158** | **63.3%** | **+0.101** | — | **+15.9** |
| **TV Config 1** (Baseline) | 2025-07-01〜2026-05-13 | 0 | 単独 | **501** | **43.5%** | — | **1.04** | +11.83 |
| ~~旧 KB 引用 (deprecate)~~ | ~~365d (2026-04-14)~~ | ~~2.14 pip RT~~ | ~~?~~ | ~~342~~ | ~~69%~~ | ~~+0.270~~ | ~~1.43~~ | ~~+92~~ |

### 重要発見: shadow (single-strategy) vs full-BT (multi-strategy) で N が 4 倍差

318d full-BT (N=158) は 365d shadow-bt (N=608) を 318/365 でスケールした期待値 (~530) と比べ **約 1/3.4**:

- 説明仮説: **Cascade CD (12 bar) + Post-SL same-dir block (40 bar)** が他 19 戦略の SL を引き金に xs_momentum エントリを大量に block している
- 結果: WR は **60.4% → 63.3% (+2.9pp)** で上昇 (他戦略の SL 後の低勝率タイミングが除外される)、EV も **-0.007 → +0.101** で改善
- これは Python BT の "execution + 防御層" が想定通りに **N を絞って WR/EV を押し上げる** ことを直接示している
- **TV 側に full-BT 相当の cascade を実装するのは現実的に困難** (TV strategy は単独実行が前提) → 真値比較には shadow-bt isolated を使うべき

### Gap の最新整理

| 比較ペア | N diff | WR diff | 説明 |
|---|---|---|---|
| Python shadow vs TV Config 1 | +107 (期間差 365/316=1.155 倍で説明可能) | **+16.9pp** | Execution layer (QH 1.7 ATR + BE + Trail + minor cascade) |
| Python 318d full vs TV Config 1 | **-343** | **+19.8pp** | Cascade CD + Post-SL block が支配的 |
| Python 318d full vs Python shadow 365d | -450 | +2.9pp | Multi-strategy cascade が N の 74% を除外、WR を 3pp 改善 |

## 構造差分マップ（Pine v2 vs Python BT loop）

両者で entry signal の論理式 (London-NY gate + ADX≥20 + mom>1.0 ATR + EMA9><EMA21 + Close confirm) は一致。ただし **execution + 防御層** が Python BT 限定で実装:

| Layer | Python BT | Pine v2 | 効果 (期待方向) | コード |
|---|---|---|---|---|
| Volume filter (`vol<100` skip) | ✅ | ❌ | N↓ | app.py:6401 |
| Bar range filter (`<min` skip) | ✅ | ❌ | N↓ | app.py:6411 |
| Session UTC<5/>=22 block (JPY 仲値除く) | ✅ | ❌ | N↓ | app.py:6417-6421 |
| Cascade CD (SL後 12bar 全戦略停止) | ✅ | ❌ | N↓, WR↑ | app.py:6388, _CASCADE_CD_DT |
| Post-SL same-dir block (40 bars) | ✅ | ❌ | N↓, WR↑ | app.py:6451-6453, _POST_SL_BLOCK_DT |
| **Quick Harvest** (`TP×0.85` → 実効 1.7 ATR) | ✅ | ❌ (固定 2.0 ATR) | **WR↑↑** | app.py:6757-6770 |
| **BE (Break-even @ ATR×0.8)** | ✅ | ❌ | **WR↑** (損→even に転換) | app.py:6787 |
| **Trailing stop (ATR×1.5 trigger, ATR×0.5 trail)** | ✅ | ❌ | **WR↑** (含み益保護) | app.py:6788-6789 |
| Friction (slippage 0.5pip + spread) | ✅ | ❌ (commission=0) | EV↓ | app.py:5127, _bt_get_slippage |
| RR<1 post-QH skip | ✅ | ❌ | N↓ | app.py:6772 |
| DT 戦略間 dedup (compute_daytrade_signal 経由) | ✅ | ❌ (単独) | N↓ | app.py:6435-6441 |

Pine v2 が持つが entry gate に使っていない (= 両者で N に影響しない):
- `disp_thr=3.0` — Python 側も scoring bonus のみで entry gate ではない (`xs_momentum.py:260-265`)

## Gap の再解釈

旧仮説: 25pp WR gap → 構造差で説明
**新仮説 (実数字基準)**: **17pp WR gap (Python 60% vs TV 43.5%)** → 構造差で**説明可能だが、Python の +EV 主張は崩壊**

注目ポイント:
- **N: Python 608 > TV 501** (107 多い) — 予想と逆。execution filter があれば Python の N は減るはず。両者の N 差は **期間差** (Python 365d vs TV ~316d) で説明可能 (365/316 = 1.155 倍、608/501 = 1.214 倍、近い)
- **PF: Python 0.99 ≈ TV 1.04** — friction 抜きの TV のほうが marginally 良い。friction を反映すると Pine v2 はおそらく PF<1.0 になり Python と整合
- **WR: 16.9pp gap** — execution layer (Quick Harvest 1.7 ATR + BE @ATR×0.8 + Trail @ATR×1.5 + Cascade CD + Post-SL block) で WR を 16-17pp 押し上げる効果として妥当な範囲

つまり整合は **おおむね取れている**。両者とも **xs_momentum × USDJPY 単体は break-even or 微 -EV**。

## 最重要結論

**xs_momentum × USDJPY の真値は測定文脈で 2 つに分かれる:**

1. **Signal 単体としての真値** (isolated, shadow-bt 365d): **PF=0.99 / EV=-0.007 / PnL=-4.0 — break-even**
2. **本番環境での真値** (full-BT 318d, 全 20 戦略同時走行 cascade 込み): **WR=63.3% / EV=+0.101 / PnL=+15.9 — 微 +EV**

つまり xs_momentum signal 自体は break-even だが、**他戦略の SL を引き金にする cascade filter で N を 1/4 に絞り込むと +EV に転化** する。これは「signal 単体は破綻だが portfolio context では生き残る」型の戦略であり、TOP 5 評価 (signal 単体基準) から外すべきだが本番デプロイは継続妥当。

KB の `[[xs_momentum]]` ページや TOP 5 列挙 (e.g. `wiki/index.md` 周辺) で **「N=342, WR=69%, EV=+0.270, PF=1.43」と古い数字が真値扱いで引用** されている可能性が高い。これらは 2026-04-14 時点の数字で、その後の改修 (v8.9 TP 縮小、Quick Harvest 等) を経た最新 Python BT では **isolated edge が消えている**。

教訓「短期BT(60d)のWR/EVを365d BTで必ず検証すべき」+「定量評価の最初のステップは changelog.md を読んで date_from を決める」の再適用。

新教訓: **single-strategy shadow-bt と multi-strategy full-bt は別物**。前者は signal の生 edge、後者は portfolio context での実エッジ。混同して引用すると判断を誤る。

## 真値階層 (memory feedback 適用後)

memory `feedback_tv_edge_discovery_loop`: "Live > TV > Python BT、乖離時は Python を疑う" の本件解釈:

1. **TV Config 1 (PF=1.04, friction=0)**: 戦略 signal 単体の真値。friction=0 で測ったので Live 反映には -0.05〜-0.10 程度の PF 低下が予想 → Live PF ≈ 0.94〜0.99
2. **Python BT shadow 365d (PF=0.99)**: signal+execution layer 込み、isolated。friction も入っているのでこのまま Live PF 推定 (= signal 単体評価)
3. **Python BT full 318d (EV=+0.101)**: portfolio context 込み、cascade で N を絞った後の実エッジ。**Live 環境はこちら**
4. **Live shadow audit**: まだ未実施 (xs_momentum_rsi shadow 2026-05-13 登録のみ、N 不足)

**3 つの BT が示す結論**: signal 単体は PF≈1.0 で break-even、portfolio context (cascade込み) では微 +EV (EV≈+0.10)。「+0.270 EV」を主張していた古い KB 数字は外れ値。Live で検証する真値は **EV=+0.10 周辺** であって +0.27 ではない。

## アクション (優先順)

### Action 1: KB から古い xs_momentum 数字を deprecate (R3, 即時) ✅ 部分完了
- ✅ `raw/bt-results/comprehensive-bt-scan-2026-04-14.md`: DEPRECATED ヘッダ追加 + TOP 5 セクションに最新数字注記 (2026-05-14 本セッション)
- ✅ `wiki/analyses/xs_momentum-tv-phase1.md`: 古い引用に inline deprecated note 追加
- ✅ `wiki/analyses/tv-bt-overlay-verification-2026-05-13.md`: 古い引用に inline deprecated note 追加
- ⏸️ `wiki/strategies/xs_momentum.md`: ファイル不存在 (作成要否はユーザー判断)
- ⏸️ `wiki/index.md`: xs_momentum 直接記述なし (TOP 5 は session-start hook 経由で注入)

### Action 1.5 (新): セッションスタート hook の TOP5 ソース修正 (構造修正)
- `scripts/hooks/session-start.sh:147` が `comprehensive-bt-scan-2026-04-14.md` を **hard-code 読込**
- これにより毎セッション古い TOP5 が context 注入される構造バグ
- 暫定対策: 該当ファイルの `## クオンツ判断` セクション内に DEPRECATED 警告を追加し、awk 抽出時に警告が含まれるよう修正済 (将来セッションは警告を直接見る)
- 根本対策: hook script を最新 BT artifact 探索に変える / または comprehensive-bt-scan を月次再生成 → **ユーザー判断必要 (task #23)**

### Action 2: 318d Python BT 完了確認 ✅
- 結果: **N=158 WR=63.3% EV=+0.101 PnL=+15.9** (`/tmp/xs_mom_bt_318d.json`)
- shadow-bt 365d isolated (N=608) と乖離 → cascade CD + Post-SL block が全 20 戦略走行下で xs_momentum N を 74% 削減
- 表に統合済

### Action 3: Phase 1 RSI filter の再評価 (pending, task #24)
- `xs_momentum-tv-phase1.md` で「TV Config 4 (Tokyo+RSI) Net=+57.37 が最良」と結論
- ただし TV friction=0。最新 Python BT が PF=0.99 ならば、RSI filter を付けても friction 反映後 +EV 維持できるか不明
- TV で commission_value/slippage を入れて Config 4 を再計測 (Phase 3 の本来の課題)

### Action 4: Step 2 ablation (signal_only / no_QH / no_BE_trail / no_cooldown) (deferred)
- env-toggle が app.py に無いため、各 variant ごとに code patch が必要 (cost 大)
- 318d full-BT 結果 (cascade による N -74%, WR +2.9pp) で directional conclusion は確立
- 残課題: QH / BE / Trail 各々の WR 寄与を分離 (~17pp WR gap を internal split)
- 着手判断: signal_only ablation 1 本だけ走らせて TV Config 1 との一致を見る方が ROI 良い

### Action 5: Live shadow N≥30 audit (pending)
- `xs_momentum_rsi` (2026-05-13 Live 登録) で N が貯まり次第、Python BT (N=608 WR=60%) の数字と Live が整合するか確認
- 整合しなければ execution layer の Live 実装に問題 → Python BT が overstated

## Related

- [tv-bt-overlay-verification-2026-05-13](tv-bt-overlay-verification-2026-05-13.md)
- [xs_momentum-tv-phase1](xs_momentum-tv-phase1.md) — Phase 1-2 結果 (TV friction=0 ベース)
- [friction-analysis](friction-analysis.md) — USDJPY 2.14 pip RT
- [bb-rsi-tv-friction-cell-audit-2026-05-14](bb-rsi-tv-friction-cell-audit-2026-05-14.md) — 別戦略の TV friction 検証先例
- `knowledge-base/raw/bt-results/xs_momentum-shadow-bt-2026-05-05.json` — 最新 365d Python BT (真値ソース)
- `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md` — **古い数字、deprecate 対象**
- `strategies/daytrade/xs_momentum.py` — Python signal
- `bt-results/tv-overlays/xs_momentum-replica.pine` — Pine v2 (素の signal)
- `app.py:6231-7000` — Python BT execution loop
