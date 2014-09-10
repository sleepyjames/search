# coding: utf-8

from datetime import date, datetime
import unittest

from .. import indexers


class BaseTest(object):
    kwargs = {}

    def indexer(self):
        return None

    def assert_indexed(self, string, expected):
        indexer = self.indexer()
        actual = indexer(string, **self.kwargs)
        self.assertEqual(sorted(actual), sorted(expected))

    def setUp(self):
        self.kwargs = {}

    tearDown = setUp


class StartswithTest(BaseTest, unittest.TestCase):
    def indexer(self):
        return indexers.startswith

    def test_1(self):
        string = u'hello'
        expected = [u'hello', u'h', u'he', u'hel', u'hell']

        self.assert_indexed(string, expected)

    def test_2(self):
        string = u'HOwDy'
        expected = [u'HOwDy', u'H', u'HO', u'HOw', u'HOwD']

        self.assert_indexed(string, expected)

    def test_3(self):
        string = u'these are words'
        expected = [u'these', u'are', u'words', u't', u'th', u'the', u'thes',
            u'a', u'ar', u'w', u'wo', u'wor', u'word']

        self.assert_indexed(string, expected)

    def test_4(self):
        string = u'buenas días'
        expected = [u'buenas', u'dias', u'días', u'b', u'bu', u'bue', u'buen',
            u'buena', u'd', u'di', u'dia', u'dí', u'día']

        self.assert_indexed(string, expected)

    def test_5(self):
        string = u'with-punctuation'
        expected = [u'with', u'punctuation', u'w', u'wi', u'wit', u'p', u'pu',
            u'pun', u'punc', u'punct', u'punctu', u'punctua', u'punctuat',
            u'punctuati', u'punctuatio']
        self.assert_indexed(string, expected)

    def test_6(self):
        self.kwargs['min_size'] = 2
        string = u'pomodoro'
        expected = ['pomodoro', 'po', 'pom', 'pomo', 'pomod', 'pomodo',
            'pomodor']

        self.assert_indexed(string, expected)
    
    def test_7(self):
        self.kwargs['max_size'] = 7
        string = u'lamentablamente, egészségére'
        expected = [u'l', u'la', u'lam', u'lame', u'lamen', u'lament',
            u'lamenta', u'e', u'eg', u'egé', u'egés', u'egész', u'egészs',
            u'egészsé', u'ege', u'eges', u'egesz', u'egeszs', u'egeszse']

        self.assert_indexed(string, expected)

    def test_8(self):
        self.kwargs['min_size'] = 3
        self.kwargs['max_size'] = 5
        string = u'hablamos things'
        expected = ['thing', 'hab', 'habl', 'habla', 'thi',
            'thin']

        self.assert_indexed(string, expected)


class ContainsTest(BaseTest, unittest.TestCase):
    def indexer(self):
        return indexers.contains

    def test_1(self):
        string = u'hello'
        expected = [u'hello', u'h', u'he', u'hel', u'hell', u'e', u'el',
            u'ell', u'ello', u'l', u'll', u'llo', u'lo', u'o']

        self.assert_indexed(string, expected)

    def test_2(self):
        string = u'HOwDy'
        expected = [u'HOwDy', u'H', u'HO', u'HOw', u'HOwD', 'O', 'Ow', 'OwD',
            'OwDy', 'w', 'wD', 'wDy', 'D', 'Dy', 'y']

        self.assert_indexed(string, expected)

    def test_3(self):
        string = u'these are words'
        expected = [u'these', u'are', u'words', u't', u'th', u'the', u'thes',
            u'h', u'he', u'hes', u'hese', u'e', u'es', u'ese', u's', u'se',
            u'a', u'ar', u'r', u're', u'w', u'wo', u'wor', u'word', u'o',
            u'or', u'ord', u'ords', u'rd', u'rds', u'd', u'ds']

        self.assert_indexed(string, expected)

    def test_4(self):
        string = u'buenas días'
        expected = [u'buenas', u'dias', u'días', u'b', u'bu', u'bue', u'buen',
            u'buena', u'u', u'ue', u'uen', u'uena', u'uenas', u'e', u'en',
            u'ena', u'enas', u'n', u'na', u'nas', u'a', u'as', u's', u'd',
            u'di', u'dia', u'dí', u'día', u'i', u'ia', u'ias', u'í', u'ía',
            u'ías']

        self.assert_indexed(string, expected)

    def test_5(self):
        string = u'with-punctuation'
        expected = [u'with', u'punctuation', u'w', u'wi', u'wit', 'i', 'it',
            'ith', 't', 'th', 'h', u'p', u'pu', u'pun', u'punc', u'punct',
            u'punctu', u'punctua', u'punctuat', u'punctuati', u'punctuatio',
            'u', 'un', 'unc', 'unct', 'unctu', 'unctua', 'unctuat', 'unctuati',
            'unctuatio', 'unctuation', 'n', 'nc', 'nct', 'nctu', 'nctua',
            'nctuat', 'nctuati', 'nctuatio', 'nctuation', 'c', 'ct', 'ctu',
            'ctua', 'ctuat', 'ctuati', 'ctuatio', 'ctuation', 'tu', 'tua',
            'tuat', 'tuati', 'tuatio', 'tuation', 'ua', 'uat', 'uati', 'uatio',
            'uation', 'a', 'at', 'ati', 'atio', 'ation', 'ti', 'tio', 'tion',
            'io', 'ion', 'o', 'on']

        self.assert_indexed(string, expected)

    def test_6(self):
        self.kwargs['min_size'] = 2
        string = u'pomodoro'
        expected = ['pomodoro', 'po', 'pom', 'pomo', 'pomod', 'pomodo',
            'pomodor', 'om', 'omo', 'omod', 'omodo', 'omodor', 'omodoro',
            'mo', 'mod', 'modo', 'modor', 'modoro', 'od', 'odo', 'odor',
            'odoro', 'do', 'dor', 'doro', 'or', 'oro', 'ro']

        self.assert_indexed(string, expected)
    
    def test_7(self):
        self.kwargs['max_size'] = 4
        string = u'forrest'
        expected = ['f', 'fo', 'for', 'forr', 'o', 'or', 'orr',
            'orre', 'r', 'rr', 'rre', 'rres', 're', 'res', 'rest', 'e',
            'es', 'est', 's', 'st', 't']

        self.assert_indexed(string, expected)


class FirstletterTest(BaseTest, unittest.TestCase):

    def indexer(self):
        return indexers.firstletter

    def test_1(self):
        string = u'hello'
        expected = [u'h']

        self.assert_indexed(string, expected)

    def test_2(self):
        string = u'HOwDy'
        expected = [u'H']

        self.assert_indexed(string, expected)

    def test_3(self):
        string = u'the words'
        expected = [u'w']

        self.kwargs['ignore'] = ['the']
        self.assert_indexed(string, expected)

    def test_4(self):
        string = u'a the framboise'
        expected = [u'f']

        self.kwargs['ignore'] = ['a', 'the']
        self.assert_indexed(string, expected)

    def test_5(self):
        string = u'The museum'
        expected = [u'm']

        self.kwargs['ignore'] = ['the']
        self.assert_indexed(string, expected)
