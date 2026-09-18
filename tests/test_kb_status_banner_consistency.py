# -*- coding: utf-8 -*-
"""canonical な decision doc の status バナーが本文の判定から取り残されていないか。

動機 (2026-09-18, PR #270): 「本体を直したのに転記先・表示側が取り残される」型の
欠陥が本 PR だけで 3 回出た:

1. 台帳 #27 の **verdict 列**が「未測定」のまま (状態列だけ直していた)
2. 台帳 #27 に**撤回済みの旧 verdict** が新版と並存 (訂正が追記になっていた)
3. pre-reg の **status バナー**が `🔒 LOCKED — 凍結済・未測定` のまま
   (§11 に FAIL を書いた後も)

3 はいずれも「§11 まで読まない読み手/ツールは canonical doc を未測定と分類する」
という同じ実害を持つ。**判定は doc の一番上に出ていなければ届かない。**

pin は構造 (見出しとバナーの関係) で書く。本文の言い回しには依存しない。
"""
import io
import re
from pathlib import Path

DECISIONS = Path(__file__).resolve().parents[1] / "knowledge-base" / "wiki" / "decisions"

# 判定を宣言する見出し (## 11. ❌ verdict: **FAIL** ... 等)
_VERDICT_HEADING = re.compile(r"^#{2,4} .*verdict.*(FAIL|PASS|PARTIAL)", re.M | re.I)
# doc 冒頭の status バナー
_STATUS = re.compile(r"^\*\*Status:[^\n]*", re.M)
# 歴史保存された過去の status は <details> に畳む規約なので検査対象外
_DETAILS = re.compile(r"<details>.*?</details>", re.S)
_UNMEASURED = re.compile("未測定|未判定")


def _visible(text):
    """<details> (不改変保存された過去の記述) を除いた、読み手が最初に見る本文。"""
    return _DETAILS.sub("", text)


def test_verdict_docs_do_not_advertise_themselves_as_unmeasured():
    seen = 0
    bad = []
    for doc in sorted(DECISIONS.glob("*.md")):
        with io.open(str(doc), encoding="utf-8") as fh:
            visible = _visible(fh.read())
        banner = _STATUS.search(visible)
        if not banner or not _VERDICT_HEADING.search(visible):
            continue
        seen += 1
        if _UNMEASURED.search(banner.group(0)):
            bad.append("%s: %s" % (doc.name, banner.group(0)[:120]))
    assert seen >= 1, "verdict 見出し + status バナーを持つ doc が消えた — 構造 pin が対象を見失っている"
    assert not bad, (
        "判定済みなのに status バナーが未測定のままの canonical doc:\n" + "\n".join(bad)
    )
