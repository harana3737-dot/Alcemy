"""Общий синтаксис Markdown-ссылок; политика адресов остаётся у рендерера."""
import re

# Сохраняем различие: книга принимает пустую цель, отдельные страницы — нет.
LINKS = {empty: re.compile(r'\[([^\]]+)\]\(((?:[^()]|\([^()]*\))' + quantifier + r')\)')
         for empty, quantifier in ((False, '+'), (True, '*'))}


def replace_links(text, render, *, empty_targets=False):
    return LINKS[empty_targets].sub(render, text)
