### lesson-sr-dict-type-error
**発見日**: 2026-04-15 | **修正**: v8.x (dt_sr_channel.py)

- **問題**: dt_sr_channel_reversal がLiveで全く機能していなかった
- **症状**: N-cache warm-startで21 strategies (22あるべき)。BT実行時に12,000+行のTypeError
- **原因**: `find_sr_levels_weighted()` はdict `{"price": float, "touches": int, ...}` を返すが、dt_sr_channel.pyは `ctx.sr_levels` を直接float比較していた。BT DTパスではL5769で `[sr["price"] for sr in ...]` 変換済みだが、Live (demo_trader) パスでは未変換のdictが渡される
- **修正**: dt_sr_channel.py内でdict/float両対応: `_sr_prices = [s["price"] if isinstance(s, dict) else s for s in ctx.sr_levels]`
- **影響**: 修正後、N-cache warm-startが22 strategiesに。365d BT: N=698, EV=+0.149, PnL=+103.3pip (Bonferroni有意)
- **教訓**: **SR levels等の共有データ構造を消費する全戦略で、データ型の防御的チェックを入れること。BTとLiveでデータ変換パスが異なる場合、戦略側で型安全を保証すべき**
