# Changelog — バージョン別変更と評価基準日

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## Fidelity Cutoff Timeline

```
2026-04-02  システム稼働開始
     |
2026-04-08  ★ Fidelity Cutoff (v6.3 SLTP修正後)
     |       ├── この日以降のデータ = "クリーンデータ"
     |       └── 以前のデータ = "バグ汚染データ"（SLTPチェッカーバグ含む）
     |
2026-04-09  v7.3-v7.6: XAU修正チェーン
     |       └── XAUデータ: v7.5以前は MAX_SL_DIST=$0.20バグで汚染
     |
2026-04-10  ★★ v8.0-v8.3: 戦略大改革
     |       ├── v8.0: vol_momentum 2.0x, engulfing_bb停止, TREND_BULL遮断
     |       ├── v8.1: TREND_BULL MR免除
     |       ├── v8.2: orb_trap PAIR_PROMOTED, vol_momentum 1.0x
     |       ├── v8.3: 確認足フィルター（bb_rsi/fib/ema_pullback）
     |       └── v8.3以降のデータ = "確認足効果測定用"
     |
2026-04-10  ★★★ v8.4: XAU停止 + Shadow汚染除去
     |       ├── XAUモード停止: scalp_xau, daytrade_xau auto_start=False
     |       ├── get_stats() is_shadow=0 フィルター追加
     |       └── v8.4以降 = "FX-only クリーンデータ"
     |
2026-04-12  Knowledge Base構築
             └── 評価基盤の確立
```

## バージョン別データ切り口

| 目的 | date_from | 除外条件 | 理由 |
|------|----------|---------|------|
| 全体傾向 | 2026-04-08 | is_shadow=0 | Fidelity Cutoff後クリーンデータ |
| **v8.3確認足効果** | **2026-04-10** | is_shadow=0 | v8.3デプロイ後のみ |
| **XAU停止効果** | **2026-04-10 夕方〜** | is_shadow=0, XAU除外 | v8.4デプロイ後 |
| **FX純粋評価** | 2026-04-08 | is_shadow=0, XAU除外 | FXのみの真のパフォーマンス |
| BT/ライブ比較 | 全期間 | なし | BT乖離幅の把握 |

## 各バージョンの影響範囲

### v7.x (2026-04-09): XAU修正チェーン
| Version | Change | Affected Strategies | Affected Data |
|---------|--------|-------------------|---------------|
| v7.3 | gold PBルーズ化+bbσバグ修正 | gold_trend_momentum | XAU DT |
| v7.4/b/c | extreme_momentum: ADX≥25, MACD-H/EMA9免除 | gold_trend_momentum | XAU DT |
| v7.5 | MAX_SL_DIST: XAU $0.20→$100 | **全XAU戦略** | ★ v7.5前のXAU SLデータは全て汚染 |
| v7.6 | Sentinel units: XAU 1000u→1u | XAU OANDA連携 | XAU audit |

### v8.x (2026-04-10〜): 戦略大改革
| Version | Change | Impact on Data |
|---------|--------|---------------|
| v8.0 | vol_momentum 2.0x, TREND_BULL全遮断 | DT TREBULLトレード消滅 |
| v8.1 | MR免除 (dt_bb_rsi_mr, dt_sr_channel_reversal通過) | DT MRトレード復活 |
| v8.2 | orb_trap PAIR_PROMOTED, vol_momentum 1.0x, bb_squeeze停止 | orb_trap OANDA送信開始 |
| **v8.3** | **確認足(bb_rsi/fib/ema_pullback)** | **★ 即死率の変化を測定する基準点** |
| **v8.4** | **XAU停止 + Shadow除去** | **★ FX-onlyの真のPnLを測定する基準点** |

## Related
- [[edge-pipeline]] — エッジ仮説の評価はどのデータ期間を使うべきか
- [[independent-audit-2026-04-10]] — "Shadow除去なしにWR/EVは信頼できない"
- [[bb-rsi-reversion]] — WR 52.2% vs 34% の矛盾はデータ期間の差
- [[friction-analysis]] — avg_friction 7.04 は XAU込み。FX-only≈2.5pip
