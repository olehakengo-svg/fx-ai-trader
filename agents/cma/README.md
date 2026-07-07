# CMA — fx-ai-trader 自律改善マルチエージェント (Claude Managed Agents)

司令塔 / 開発 / リサーチ / レビュー(反証) の4エージェントで、負け要因の発見 →
shadow-first 検証 → 条件付き自動 LIVE flip(上限付) を回す。設計記録は親 session の
memory `project_cma_fxai_autoimprove_2026_06_16` を参照。

## 構成

| ファイル | 役割 |
|---|---|
| `env.self-hosted.yaml` | self_hosted environment (tool は worker がローカル実行) |
| `reviewer.agent.yaml` | 反証エージェント = 過剰最適化への防壁 |
| `dev.agent.yaml` | 実装/BT/PR (merge禁止・LIVE触らない) |
| `research.agent.yaml` | 仮説生成 (pre-reg 台帳前提) |
| `coordinator.agent.yaml` | 司令塔 (北極星=月利 / 合否=rubric / LIVEは custom tool 提案) |
| `edge_promotion_rubric.md` | 昇格の合否基準 (出口ゲート) |
| `setup.sh` | 環境+4エージェントを `ant` で作成 → `ids.env` 出力 |
| `worker.py` | self_hosted tool worker (常駐・ローカル実行) |
| `smoke_reviewer.py` | **STEP B** reviewer 単体スモークテスト |
| `driver.py` | 本番ループ + LIVE flip Gate 検査 (実弾の最終防壁) |

## Gate (2026-06-16 確定 / N floor撤廃・Wilson主導)

- 入口(shadow投入)=素通り: pre-reg登録 ∧ BT符号が破滅的に負でない、だけ
- 出口(LIVE昇格): N≥20 ∧ Wilson_lo≥0.40(BH-FDR q=0.10補正後) ∧ WF≥3/4(登録時12y履歴) ∧ friction≤TP10%
- lot ランプ: N≥20→1000u / N≥35→2500u / N≥50→5000u
- 低N(20-34)は高速demote (Live N≥5∧EV<0)、quarter-Kelly、同時≤12、週≤3
- sizing引き上げは閾値に関わらず人間承認

## 手順

```sh
# A. 作成 (一度だけ)
ant auth login                 # 未認証なら
bash agents/cma/setup.sh       # → agents/cma/ids.env

# Console で self_hosted environment の "Generate environment key" → 控える
source agents/cma/ids.env
export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-...

# B. reviewer 単体スモーク (推奨: 最初にここ)
#   terminal 1:
python agents/cma/worker.py
#   terminal 2:
export ANTHROPIC_API_KEY=sk-ant-...
python agents/cma/smoke_reviewer.py
#   → Wilson/WF/BH-FDR が一次データで正しく回り、迷えば reject するのを確認

# C. dev 単体 (PR まで通るか) — GitHub MCP vault が要る
#   GitHub MCP の OAuth cred を vault に登録 (mcp_oauth):
#   ant beta:vaults create --name github-mcp ...
#   ant beta:vaults:credentials create --vault-id vlt_... \
#     --auth '{type: mcp_oauth, mcp_server_url: "https://api.githubcopilot.com/mcp/", access_token: "...", refresh: {...}}'
#   export GITHUB_VAULT_ID=vlt_...

# D. 本番ループ (driver.py)。最初は LIVE flip は DRYRUN のまま判定だけ観察。
python agents/cma/driver.py
#   gates が想定どおり締まるのを数回確認 → driver.py の subprocess.run(...) を有効化
```

## 安全装置
- `driver.py` の LIVE flip は既定 **DRYRUN** (実 env を点灯しない)。検証後に配線。
- LIVE env / `_PAIR_LOT_BOOST` / sizing は bash 面に出さず custom tool 経由のみ。
- merge は人間/CI。エージェントは PR まで。
- 既存 watchdog (Live N≥10 EV<0 自動demote) / 日次CB(−30pip) と併存。
