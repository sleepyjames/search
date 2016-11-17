# -*- coding: utf-8 -*-
from djangae.test import TestCase

from ..utils import get_ascii_string_rank


class TestUtils(TestCase):

    def test_ascii_rank(self):
        from text_unidecode import unidecode

        strings = [u"a", u"az", u"aaaa", u"azzz", u"zaaa", u"jazz", u"ball", u"a ball", u"łukąźć", u"ołówek", u"♧"]

        ranks = [get_ascii_string_rank(s) for s in strings]

        # Ordering the ranks should result in the same order as the strings.
        self.assertEqual(
            [get_ascii_string_rank(s) for s in sorted([unidecode(s) for s in strings])],
            sorted(ranks)
        )
