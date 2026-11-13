"""Сохраняем различия рендереров при общем разборе ссылок."""
import unittest
from markdown_links import replace_links
from master_html import render_inline
from player_book import inline


class MarkdownLinksTests(unittest.TestCase):
    def test_nested_parentheses_and_adjacent_links(self):
        text = '[один](a(b).md) [два](#якорь)'
        self.assertEqual(replace_links(text, lambda m: m[2]), 'a(b).md #якорь')

    def test_empty_target_is_an_explicit_policy(self):
        self.assertEqual(replace_links('[текст]()', lambda m: 'ссылка'), '[текст]()')
        self.assertEqual(replace_links('[текст]()', lambda m: 'ссылка', empty_targets=True), 'ссылка')

    def test_renderers_keep_their_link_policy(self):
        self.assertIn('href="другой.html"', render_inline('[текст](другой.md)', lambda _: 'другой.html'))
        self.assertNotIn('<a ', inline('[текст](другой.md)'))
        self.assertEqual(inline('`[текст](#x)`'), '<code>[текст](#x)</code>')
