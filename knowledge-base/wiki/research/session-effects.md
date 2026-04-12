# Session Effects — セッション境界の非対称性

## Core Theory
FX市場はセッション（Tokyo/London/NY）の開始・終了時に構造的な非対称性を持つ。これはディーラーのインベントリ管理、Fixingフロー、流動性の急変に起因する。

## Key Papers
- [[andersen-2003]]: マクロ経済指標発表直後の価格ダイナミクス。発表後5分の非対称的反応
- Evans & Lyons (2002): FXのorder flowが価格に与える影響。Fix時間帯に有意な価格変動
- Bjonnes & Rime (2005): ディーラーのinventory管理。セッション終了前にポジション平準化

## Implemented Strategies
- **tokyo_nakane_momentum**: 仲値(UTC 00:45)のDOWN→BUY非対称性 (Andersen 2003)
- **orb_trap**: London/NY ORのフェイクアウト (session boundary liquidity)

## Observed in Production
| Session | Scalp Avg Slippage | Spread | Best Hours |
|---------|-------------------|--------|------------|
| London | 0.31pip | 0.55pip | **UTC 15 (WR=65.6%, EV=+1.47)** |
| Tokyo | 1.04pip | 2.10pip | UTC 1 (WR=58.3%, EV=+1.68) |
| NY | 2.48pip | 4.82pip | (XAU-inflated) |

## Unexplored Extensions
1. **London Fixing (UTC 16:00)**: 4pm Fix creates massive order flows. EUR/JPYのscalp利益60%がUTC 15に集中 → Fix前のポジショニング効果？
2. **NY Close (UTC 21:00)**: ディーラーのbook squaring → 方向転換の予測可能性
3. **Sunday Gap**: 週末ギャップの平均回帰 (Bollen & Inder 2002)
4. **Month-end Fix**: 月末リバランスフロー (Melvin & Prins 2015)

## Related
- [[microstructure-stop-hunting]] — スイープはセッション境界で頻発
- [[friction-analysis]] — London=最低摩擦、Tokyo=2x、NY=4x（XAU含む）
