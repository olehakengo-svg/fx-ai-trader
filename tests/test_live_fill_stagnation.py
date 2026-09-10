"""LIVE 約定停止の検知 pin (rule:R3, 2026-09-03).

**発見の経緯**: 2026-08-26 14:59 UTC を最後に LIVE 約定 (``oanda_trade_id``
を持つ行) が 133 市場オープン時間 = 実時間 7.5 日ゼロだったが、9 個の検知器
すべてが無音だった。原因は estimand の取り違えである:

``live_n_stagnation`` と画面の ``trade_row`` は ``demo_trades`` **全体**の
最終書込みを見ている。しかし ``demo_trades`` の **99.8% は shadow 行**
(本番実測 501 行中 LIVE は 1 行) で、shadow は毎日 80-111 行流れる。
つまり「最終行」は LIVE が完全に止まっても常に数分以内であり、
これらの系列は**約定の停止を原理的に検知できない**。

にもかかわらず ``check_engine_tick_stall`` の estimand 表は
``live_n_stagnation`` を「約定が出たか (ゲート通過後)」と記述していた。
**表が実装について偽を述べていた** — ZN 教訓 (計装契約バグ) の系列。

本ファイルが pin するのは 4 つの性質:

1. 新検知器が LIVE 約定だけを見る (shadow が流れていても発火する)
2. 週末は市場オープン時間で除外する (実時間だと毎週末誤発火する)
3. 欠損・破損・版ずれで**沈黙しない** (126 日 no-op の直接の原因)
4. **main() から実際に呼ばれている** — 検知器を書いても配線しなければ
   全テスト green のまま無音になる (2026-08-28 に counterfactual ⑥ が
   初回素通りした実績あり)
"""
from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "anomaly_watcher_lf", ROOT / "scripts" / "anomaly_watcher.py"
)
aw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aw)

WATCHER_SRC = (ROOT / "scripts" / "anomaly_watcher.py").read_text(encoding="utf-8")

# 木曜 12:00 UTC — ここから遡る窓に週末を跨がせるかを自由に選べる基準点。
THU = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)


def _status(last_at: datetime | str | None, st: str = "ok", **extra) -> dict:
    """/api/demo/status の鮮度部分だけを本番と同じ形で組む。"""
    at = last_at.isoformat() if isinstance(last_at, datetime) else last_at
    out = {
        "last_live_fill_row_status": st,
        "last_live_fill_row_at": at,
        # LIVE が止まっていても shadow は流れ続ける、という現実の形を
        # 必ず同居させる。これが無いとテストが問題そのものを再現しない。
        "last_trade_row_status": "ok",
        "last_trade_row_at": (THU - timedelta(minutes=3)).isoformat(),
        "last_candidate_row_status": "ok",
        "last_candidate_row_at": (THU - timedelta(minutes=2)).isoformat(),
    }
    out.update(extra)
    return out


class TestFiresOnLiveFillDrought:
    def test_fires_past_threshold(self):
        """閾値超えで発火し、市場オープン時間と実時間の両方を報告する。"""
        last = THU - timedelta(hours=200)  # 週末 1 回込み → open ≈ 152h
        ev = aw.check_live_fill_stagnation(_status(last), now=THU)
        assert len(ev) == 1
        assert ev[0]["type"] == "live_fill_stagnation"
        assert ev[0]["market_open_hours_since"] >= aw.LIVE_FILL_STAGNATION_HOURS
        # 実時間も併記されること (どちらか一方だと読み手が誤解する)
        assert ev[0]["hours_since_last_live_fill"] == pytest.approx(200, abs=0.2)
        assert ev[0]["threshold_hours"] == aw.LIVE_FILL_STAGNATION_HOURS

    def test_silent_below_threshold(self):
        assert aw.check_live_fill_stagnation(
            _status(THU - timedelta(hours=48)), now=THU
        ) == []

    def test_shadow_freshness_does_not_suppress_it(self):
        """**本件の中核**: shadow 行が数分前でも LIVE の停止で発火する。

        旧経路 (``check_live_n_stagnation``) は同じ入力で沈黙する。
        両者を同じ status に対して走らせ、**片方だけが鳴る**ことを pin する
        — これが 2026-08-26〜09-03 に実際に起きた状態そのものである。
        """
        st = _status(THU - timedelta(hours=200))
        assert st["last_trade_row_status"] == "ok"  # shadow は新鮮

        fired = aw.check_live_fill_stagnation(st, now=THU)
        assert len(fired) == 1, "shadow が新鮮だと LIVE 停止を見逃している"

        # 旧検知器を本番同型の入力 (shadow 行ばかりの trades) で走らせる
        shadow_rows = [
            {"entry_time": (THU - timedelta(minutes=i)).isoformat(), "oanda_trade_id": ""}
            for i in range(1, 60)
        ]
        assert aw.check_live_n_stagnation({}, shadow_rows, now=THU, trades_ok=True) == [], (
            "前提が崩れた: 旧検知器がここで鳴るなら本 PR の動機が変わる"
        )


class TestWeekendClock:
    def test_weekend_is_excluded(self):
        """実時間では閾値超えだが市場オープン換算では下回る窓で沈黙する。

        週末を換算しないと金曜最終約定が毎週末必ず誤発火する。
        """
        # 実時間 144h だが週末 48h を含む → open ≈ 96h < 120h
        last = THU - timedelta(hours=144)
        ev = aw.check_live_fill_stagnation(_status(last), now=THU)
        wall = 144.0
        open_h = aw._market_open_hours(last, THU)
        assert wall >= aw.LIVE_FILL_STAGNATION_HOURS > open_h, (
            f"テスト前提が崩れた (wall={wall} open={open_h})"
        )
        assert ev == [], "週末を実時間で数えて誤発火している"


class TestNeverSilentOnBrokenInput:
    """「無ければ skip」が 126 日 no-op を生んだ。沈黙は許さない。"""

    def test_missing_field_is_reported(self):
        ev = aw.check_live_fill_stagnation({"last_trade_row_status": "ok"}, now=THU)
        assert [e["type"] for e in ev] == ["live_fill_freshness_missing"]

    def test_query_error_is_reported(self):
        ev = aw.check_live_fill_stagnation(
            _status(None, st="error", row_freshness_error="disk I/O error"), now=THU
        )
        assert [e["type"] for e in ev] == ["live_fill_freshness_error"]
        assert "disk I/O error" in ev[0]["detail"]

    def test_unparseable_timestamp_is_reported(self):
        ev = aw.check_live_fill_stagnation(_status("not-a-date"), now=THU)
        assert [e["type"] for e in ev] == ["live_fill_freshness_error"]

    def test_no_rows_is_not_an_alert(self):
        """LIVE 約定が DB 開始以来ゼロ = 初期状態であって異常ではない。

        ``no_rows`` と ``error`` を畳まないこと (PR #207 の設計罠)。
        """
        assert aw.check_live_fill_stagnation(_status(None, st="no_rows"), now=THU) == []

    def test_no_table_is_not_an_alert(self):
        """旧 DB 互換。障害ではない。"""
        assert aw.check_live_fill_stagnation(_status(None, st="no_table"), now=THU) == []

    def test_db_reported_unparseable_is_an_alert_not_silence(self):
        """**DB 側が ``unparseable`` を返した場合を黙って捨てない。**

        counterfactual で発見 (2026-09-03): ``no_rows`` の早期 return を消して
        も全テストが green のままだった = ``st != "ok"`` の総括 return が
        すべてを飲み込んでおり、``unparseable`` (= 行はあるが時刻が壊れて
        いる = 本物の異常) まで沈黙していた。本 PR が直している「静かに
        skip」型の穴を、新しい検知器に作り直すところだった。
        """
        ev = aw.check_live_fill_stagnation(
            _status("garbage-from-db", st="unparseable"), now=THU
        )
        assert [e["type"] for e in ev] == ["live_fill_freshness_error"], (
            "DB 報告の unparseable が黙って捨てられている"
        )


class TestWiredIntoMain:
    """検知器は**呼ばれて初めて**検知器になる (2026-08-28 の教訓)。

    pin は「性質」を書く: main() の本体の中で呼ばれ、その結果が
    ``all_events`` に入っていること。ファイル全体へのリテラル一致にすると
    ①等価リファクタで配線無傷のまま落ち ②main() の外にあっても通る、の
    両方向に誤る (PR #209 の是正と同じ形)。
    """

    @staticmethod
    def _main_body() -> str:
        m = re.search(r"^def main\(", WATCHER_SRC, re.M)
        assert m, "main() が見つからない"
        rest = WATCHER_SRC[m.end():]
        nxt = re.search(r"^def ", rest, re.M)
        return WATCHER_SRC[m.start(): m.end() + (nxt.start() if nxt else len(rest))]

    def test_called_from_main(self):
        body = self._main_body()
        assert "check_live_fill_stagnation(" in body, (
            "check_live_fill_stagnation が main() から呼ばれていない "
            "(write-only 検知器 = 全テスト green のまま無音)"
        )

    def test_result_reaches_all_events(self):
        body = self._main_body()
        assert re.search(
            r"all_events\.extend\(\s*check_live_fill_stagnation\(", body
        ), "呼んではいるが all_events に入れていない (通知経路に届かない)"

    def test_notification_budget_registered(self):
        """通知バケットに載っていないと抑制ロジックの既定に落ちる。"""
        assert "live_fill_stagnation" in aw.NOTIFY_EVERY_HOURS


class TestDbSeriesActuallyFiltersLiveRows:
    """``live_fill`` 系列が本当に LIVE 行だけを見ていることの**行動証拠**.

    構文 pin ではなく実 DB で確かめるのが肝。もし誰かが SQL を
    ``SELECT MAX(created_at) FROM demo_trades`` に「単純化」しても、
    構文 pin なら書き換え方によっては通ってしまう。しかしこのテストは
    **shadow だけを新しく書いたときに live_fill が動かない**という
    観測可能な性質を見るので、その退化を必ず捕まえる。

    これは本 PR が修正しているバグそのもの (shadow と LIVE の畳み込み) の
    再発検査でもある。
    """

    @pytest.fixture
    def db(self):
        import os
        import tempfile

        from modules.demo_db import DemoDB

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield DemoDB(db_path=path)
        os.unlink(path)

    def test_empty_db_reports_no_rows(self, db):
        f = db.get_row_freshness()
        assert f["last_live_fill_row_status"] == "no_rows"
        assert f["last_live_fill_row_at"] is None

    def test_contract_keys_always_present(self, db):
        f = db.get_row_freshness()
        for key in (
            "last_live_fill_row_at",
            "last_live_fill_row_age_sec",
            "last_live_fill_row_status",
        ):
            assert key in f, f"missing contract key: {key}"

    def test_shadow_only_writes_leave_live_fill_empty(self, db):
        """**中核の行動証拠**: shadow を何行書いても LIVE 系列は無反応。"""
        for i in range(5):
            db.open_trade(
                "BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65,
                is_shadow=True,
                entry_time=(datetime.now(timezone.utc)
                            - timedelta(minutes=10 - i)).isoformat(),
            )
        f = db.get_row_freshness()
        assert f["last_trade_row_status"] == "ok", "前提: shadow 行は書けている"
        assert f["last_live_fill_row_status"] == "no_rows", (
            "shadow 行が LIVE 約定として数えられている "
            "(= 本 PR が直したバグの再発)"
        )

    def test_live_row_is_picked_up(self, db):
        db.open_trade(
            "BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65,
            oanda_trade_id="12345",
        )
        f = db.get_row_freshness()
        assert f["last_live_fill_row_status"] == "ok"
        assert 0 <= f["last_live_fill_row_age_sec"] < 120

    def test_later_shadow_does_not_refresh_live_series(self, db):
        """LIVE の後に shadow を書いても LIVE 系列の時刻は前進しない。

        これが崩れると「shadow が流れている限り LIVE は永遠に新鮮」という
        元のバグに戻る。
        """
        import sqlite3

        db.open_trade(
            "BUY", 150.5, 150.2, 151.0, "dual_sr_bounce", 65,
            oanda_trade_id="12345",
        )
        # `created_at` は DB 側 DEFAULT (datetime('now')) の**秒精度**なので、
        # そのままだと LIVE 行と直後の shadow 行が同一値になり、この pin が
        # 何も判定しなくなる (最初にその形で書いて実際に無力だった)。
        # LIVE 行を明示的に過去へ倒して 2 系列を分離する。
        with sqlite3.connect(db._path) as conn:
            conn.execute(
                "UPDATE demo_trades SET created_at = ? "
                "WHERE oanda_trade_id = '12345'",
                ("2026-09-01 00:00:00",),
            )
            conn.commit()

        before = db.get_row_freshness()["last_live_fill_row_at"]
        assert before == "2026-09-01 00:00:00", f"前提が崩れた: {before!r}"

        for i in range(3):
            db.open_trade(
                "SELL", 150.5, 150.8, 150.0, "dual_sr_bounce", 65,
                is_shadow=True,
                entry_time=(datetime.now(timezone.utc)
                            - timedelta(minutes=3 - i)).isoformat(),
            )

        after = db.get_row_freshness()
        assert after["last_trade_row_at"] != before, (
            "前提: shadow 書込みで trade 系列は前進しているはず"
        )
        assert after["last_live_fill_row_at"] == before, (
            "shadow の書込みが LIVE 系列を新鮮に見せている "
            "(= 本 PR が直したバグの再発)"
        )


class TestThresholdIsSsotAndCalibrated:
    def test_threshold_comes_from_freshness_policy(self):
        """閾値を watcher 側に書き写さない (PR #199/#209 で踏んだ型)。

        ⚠️ 初版は ``aw.X is fp.X`` だけを見ていたが、これは **counterfactual
        を素通りさせた** (2026-09-03): watcher に ``= 120`` とベタ書きしても
        120 は CPython の小整数キャッシュ域なので ``is`` が True になり、
        テストは green のままだった。値の一致では「書き写し」を検出できない
        — 検出すべきは **束縛が _fp 由来であるという構造**である。
        """
        import modules.freshness_policy as fp

        assert aw.LIVE_FILL_STAGNATION_HOURS == fp.LIVE_FILL_STAGNATION_HOURS

        m = re.search(
            r"^LIVE_FILL_STAGNATION_HOURS\s*=\s*(.+)$", WATCHER_SRC, re.M
        )
        assert m, "watcher に LIVE_FILL_STAGNATION_HOURS の束縛が無い"
        assert m.group(1).strip() == "_fp.LIVE_FILL_STAGNATION_HOURS", (
            "閾値が SSOT (modules/freshness_policy) からでなく watcher に "
            f"書き写されている: {m.group(1).strip()!r}"
        )

    def test_threshold_clears_observed_post_carveout_max(self):
        """carve-out 後 (2026-07-29〜) の実測到着間隔 max = 75.3 市場オープン
        時間。閾値がこれを下回ると正常な閑散で誤発火する。

        この 15 本は 2026-09-03 に本番 /api/demo/trades 6,000 行から実測した
        ものを凍結してある (較正の根拠を後から検証できるようにするため)。
        """
        observed_post_carveout = [
            0.6, 2.6, 2.7, 7.8, 17.0, 19.1, 22.7, 30.0,
            33.1, 42.2, 43.2, 60.8, 65.8, 67.3, 75.3,
        ]
        assert aw.LIVE_FILL_STAGNATION_HOURS > max(observed_post_carveout), (
            "閾値が実測 max を下回る = 正常な閑散で誤発火する"
        )
        fires = [g for g in observed_post_carveout
                 if g >= aw.LIVE_FILL_STAGNATION_HOURS]
        assert fires == [], f"carve-out 後の実測で誤発火する: {fires}"

    def test_threshold_still_catches_the_incident_that_motivated_it(self):
        """2026-09-03 実測の 133.3 市場オープン時間ドリフトを取り逃さない。

        閾値を上げすぎると「誤発火ゼロだが何も捕まえない」に退化する。
        下側 (誤発火) と上側 (見逃し) の両方を pin して初めて較正が固定される。
        """
        assert aw.LIVE_FILL_STAGNATION_HOURS <= 133.3, (
            "閾値が高すぎて本検知器の動機となった実ドリフトを見逃す"
        )
