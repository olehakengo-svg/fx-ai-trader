"""/healthz/http — Render health check 用の軽量 DB プローブ (rule:R3, 2026-09-22).

なぜ既存の /healthz ではないか: /healthz は ``get_status()`` (StatusHeal =
worker 側で 24 モードのエンジンを起こす副作用) と ``request_tick()`` を呼ぶ。
Render の health check は数十秒間隔で叩くので、それを StatusHeal 経路に
接続すると**起動直後に worker エンジンを必ず起こす**ことになる (master 側
エンジンとの二重化を決定的にする)。プローブは「HTTP 層が生きて DB を開けるか」
だけを答える。

固定する性質:
  A. 200 を返し、fresh な sqlite3 接続で SELECT 1 が通ったことを報告する
     (2026-09-22 の全盲 worker では**この connect が永久ハング**する = 検出対象そのもの)
  B. StatusHeal / request_tick を呼ばない (テキスト pin)
  C. render.yaml の healthCheckPath がこのルートを指す (配線 pin)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_probe_returns_ok_with_db_probe(flask_client):
    resp = flask_client.get("/healthz/http")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["status"] == "ok"
    assert body["db_ok"] is True
    assert isinstance(body["serving_pid"], int)
    assert "db_probe_ms" in body


def test_probe_does_not_touch_status_heal_or_tick():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    start = src.index('@app.route("/healthz/http")')
    end = src.index("@app.route(", start + 10)
    # docstring (設計理由の説明で get_status に言及する) を除いたコード本体だけを見る
    body = re.sub(r'"""[\s\S]*?"""', "", src[start:end])
    assert "get_status(" not in body, "プローブが StatusHeal 経路 (get_status) を呼んでいる"
    assert "request_tick(" not in body, "プローブが request_tick を呼んでいる"
    assert "sqlite3" in body and "SELECT 1" in body, "fresh 接続の SELECT 1 プローブが無い"


def test_render_health_check_path_points_at_the_probe():
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    m = re.search(r"^\s*healthCheckPath:\s*(\S+)", text, re.M)
    assert m, "render.yaml に healthCheckPath が無い (HTTP 全盲は Render の TCP チェックでは数時間検出されない)"
    assert m.group(1) == "/healthz/http"
