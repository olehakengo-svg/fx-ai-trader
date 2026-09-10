"""Tests for pure helpers in tools/mof_statements_ingest.py (no network)."""
from tools import mof_statements_ingest as ing


INDEX_HTML = """
<ul>
<li><a href="./202304.html">令和5年4月</a></li>
<li><a href="./202508.html">令和7年8月</a></li>
<li><a href="./201010.html">平成22年10月</a></li>
<li><a href="/public_relations/conference/index.html">大臣等記者会見</a></li>
</ul>
"""

MONTH_HTML = """
<div><a href="./my20240426.html">4月26日 </a><a href="./my20240402.html">4月2日 </a>
<a href="./index.html">戻る</a></div>
"""

# pre-2023-04 originals (WARP captures) use the .htm extension
MONTH_HTML_LEGACY = """
<div><a href="./my20220913.htm">9月13日 </a><a href="./my20220922.htm">9月22日 </a></div>
"""

INDEX_HTML_LEGACY = '<li><a href="./202209.htm">令和4年9月</a></li>'

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>財務省：新着RSS</title>
<item><title>外国為替平衡操作の実施状況（令和8年7月～令和8年7月）</title>
<link>https://www.mof.go.jp/policy/international_policy/reference/feio/data/monthly/20260829.html</link>
<pubDate>Fri, 29 Aug 2026 08:00:00 +0900</pubDate></item>
<item><title>5年利付国債の入札結果</title>
<link>https://www.mof.go.jp/jgbs/auction/resul20260818a.htm</link>
<pubDate>Tue, 18 Aug 2026 04:00:00 +0900</pubDate></item>
</channel></rss>
"""


def test_extract_month_links_returns_sorted_unique_stamps():
    assert ing.extract_month_links(INDEX_HTML) == ["201010", "202304", "202508"]


def test_extract_conf_links_returns_sorted_unique():
    assert ing.extract_conf_links(MONTH_HTML) == ["my20240402.html", "my20240426.html"]


def test_extract_links_accept_legacy_htm_extension():
    assert ing.extract_month_links(INDEX_HTML_LEGACY) == ["202209"]
    assert ing.extract_conf_links(MONTH_HTML_LEGACY) == ["my20220913.htm", "my20220922.htm"]


def test_parse_rss_items():
    items = ing.parse_rss_items(RSS_XML)
    assert len(items) == 2
    assert items[0]["link"].endswith("20260829.html")
    assert "平衡操作" in items[0]["title"]


def test_filter_fx_items_keeps_only_fx_related():
    items = ing.parse_rss_items(RSS_XML)
    fx = ing.filter_fx_items(items)
    assert len(fx) == 1
    assert "平衡操作" in fx[0]["title"]
