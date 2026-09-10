#!/usr/bin/env python3
"""E23 central_bank_statement_text — Apel–Blix Grimaldi (2012) hawk–dove 凍結辞書スコアラー.

出典 (観測窓 2014+ に全面先行 = 外部凍結特徴量、in-house 語彙 DoF の構造封鎖):
  Apel, M. & M. Blix Grimaldi (2012), "The Information Content of Central Bank
  Minutes", Sveriges Riksbank Working Paper Series No. 261.
  http://archive.riksbank.se/Documents/Rapporter/Working_papers/2012/rap_wp261_120426.pdf
  (2026-09-10 取得・実在確認済み)

  - 名詞 11 語 = 同 WP Appendix の英訳列を逐語転記 (wildcard = 語幹前方一致、
    複合語を含む — 例 "inflation expectations")。
  - 形容詞 = hawkish {high*, strong*, increasing/increase*, fast*} /
    dovish {low*, weak*, decreasing/decreas*, slow*} (同 Appendix 英訳列)。
  - two-word combination = 形容詞トークンの直後に名詞 (文内隣接のみ、§6)。
  - Net Index (net-hawkishness) = (#hawk − #dove) / (#hawk + #dove + 1)
    (同 §6、Birz & Lott 2011 様式 — 分子に +1 を置く表記とも恒等)。
  - unemployment のみ極性反転 (strong/increasing unemployment = dovish)。反転は
    WP の意味論に内在し、二次文献 (Bennani ほか; Quality & Quantity 2024,
    doi:10.1007/s11135-024-01896-9) が ABG 辞書の仕様として明文化している。

規律 (E23 pre-reg C5 封鎖):
  - 語彙の追加・削除・重み付け・否定処理の追加は恒久禁止 (凍結辞書)。
  - 本モジュールは「テキスト → スコア」のみ。価格・リターン・イベントとの結合は
    行わない (それは pre-reg LOCK 後の測定ハーネスの領分)。
"""
from __future__ import annotations

import re

# ─── 凍結語彙 (WP 261 Appendix 英訳列、逐語) ─────────────────────────────────
# 名詞: 語幹前方一致 (wildcard)。2 トークン名詞は先に照合 (longest-match-first)。
NOUN_STEMS_2 = (("oil", "price"), ("cyclical", "position"))
NOUN_STEMS_1 = ("inflation", "price", "wage", "growth", "development",
                "unemployment", "employment", "recovery", "cost")
# ⚠ 照合順序が意味を持つ: "unemployment" は "employment" を含まないトークンだが、
#   前方一致では "unemployment".startswith("employment") == False なので衝突しない。
#   ただし明示順 (長い語幹が先) を凍結し、test で pin する。

# unemployment のみ極性反転 (hawkish 形容詞 + unemployment → dovish、逆も同様)
INVERTED_NOUNS = ("unemployment",)

HAWKISH_ADJ_STEMS = ("high", "strong", "increas", "fast")
DOVISH_ADJ_STEMS = ("low", "weak", "decreas", "slow")

_SENT_SPLIT = re.compile(r"[.!?;:]")
_TOKEN = re.compile(r"[a-z]+")


def _match_adj(token: str) -> str | None:
    """トークンが hawkish/dovish 形容詞語幹に前方一致するか。'h' / 'd' / None。"""
    for stem in HAWKISH_ADJ_STEMS:
        if token.startswith(stem):
            return "h"
    for stem in DOVISH_ADJ_STEMS:
        if token.startswith(stem):
            return "d"
    return None


def _match_noun(tokens: list[str], i: int) -> tuple[str, int] | None:
    """位置 i から名詞照合。(matched_stem, 消費トークン数) / None。2 トークン優先。"""
    if i + 1 < len(tokens):
        for a, b in NOUN_STEMS_2:
            if tokens[i].startswith(a) and tokens[i + 1].startswith(b):
                return (f"{a} {b}", 2)
    for stem in NOUN_STEMS_1:
        if tokens[i].startswith(stem):
            return (stem, 1)
    return None


def count_bigrams(text: str) -> dict:
    """凍結 two-word combination の計数。

    戻り値 = {"hawk": int, "dove": int, "matches": [(polarity, adj, noun), ...]}
    文境界 ([.!?;:]) を跨ぐ隣接は照合しない。
    """
    hawk = dove = 0
    matches: list[tuple[str, str, str]] = []
    for sentence in _SENT_SPLIT.split(text.lower()):
        tokens = _TOKEN.findall(sentence)
        for i, tok in enumerate(tokens[:-1]):
            pol = _match_adj(tok)
            if pol is None:
                continue
            noun = _match_noun(tokens, i + 1)
            if noun is None:
                continue
            stem, _ = noun
            if stem in INVERTED_NOUNS:
                pol = "d" if pol == "h" else "h"
            if pol == "h":
                hawk += 1
            else:
                dove += 1
            matches.append((pol, tok, stem))
    return {"hawk": hawk, "dove": dove, "matches": matches}


def net_hawkishness(text: str) -> float:
    """ABG §6 Net Index: (#hawk − #dove) / (#hawk + #dove + 1)。範囲 (−1, 1)。"""
    c = count_bigrams(text)
    return (c["hawk"] - c["dove"]) / (c["hawk"] + c["dove"] + 1)


def delta_net_hawkishness(text_t: str, text_prev: str) -> float:
    """E23 primary シグナルの素材: 同一中銀・同一文書種の声明間差分 ΔNH。"""
    return net_hawkishness(text_t) - net_hawkishness(text_prev)
