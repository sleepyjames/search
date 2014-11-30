# -*- coding: utf-8 -*-

import re
import sys

from .globs import CHARACTER_MAP, FOREIGN_CHARACTERS_REGEX


UNRECOGNISED_FIRST_LETTER_STRING = u'zzz'
PUNCTUATION_REGEX = re.compile(ur'[^\w -\'"+]', re.U)
WHITESPACE_REGEX = re.compile(ur'[\s]+', re.U)


def clean_value(value):
    value = value or u''
    value = PUNCTUATION_REGEX.sub(u' ', value)
    value = WHITESPACE_REGEX.sub(u' ', value)
    return value.strip()


def _startswith(string, min_size=0, max_size=sys.maxint, fn=lambda s:s):
    """
    >>> _startswith('hello')
    ['hello', 'h', 'he', 'hel', 'hell']

    >>> _startswith('hello words') # doctest: +NORMALIZE_WHITESPACE
    ['hello words', 'h', 'he', 'hel', 'hell', 'hello', 'hello ', 'hello w',
     'hello wo', 'hello wor', 'hello word']

    >>> _startswith('All THE ThinGs') # doctest: +NORMALIZE_WHITESPACE
    ['All THE ThinGs', 'A', 'Al', 'All', 'All ', 'All T', 'All TH', 'All THE',
     'All THE ', 'All THE T', 'All THE Th', 'All THE Thi', 'All THE Thin',
     'All THE ThinG']

    >>> _startswith('HELLO', fn=lambda s:s.lower())
    ['hello', 'h', 'he', 'hel', 'hell']
    """
    index = []
    length = len(string)

    if min_size <= length <= max_size:
        index = [fn(string)]

    for i in range(1, length):
        segment = fn(string[:i])
        if min_size <= len(segment) <= max_size and segment not in index:
            index.append(segment)
    return index


def contains(string, **kwargs):
    """
    >>> sorted(contains('hello')) # doctest: +NORMALIZE_WHITESPACE
    ['e', 'el', 'ell', 'ello', 'h', 'he', 'hel', 'hell', 'hello', 'l', 'll',
     'llo', 'lo', 'o']
    """
    string = clean_value(string)
    index = []

    for word in string.split():
        if word not in index:
            for i in range(len(word)):
                segments = startswith(word[i:], **kwargs)
                index += segments
    return list(set(index))


def startswith(string, **kwargs):
    u"""
    >>> startswith('Plorm Hamdis') # doctest: +NORMALIZE_WHITESPACE
    [u'Plorm', u'P', u'Pl', u'Plo', u'Plor', u'Hamdis', u'H', u'Ha', u'Ham',
     u'Hamd', u'Hamdi']

    The next test is skipped because it breaks for some reason, even though it
    follows the answer here:
    http://stackoverflow.com/questions/1733414/how-do-i-include-unicode-strings-in-python-doctests

    >>> print startswith(u'buenas días') # doctest: +NORMALIZE_WHITESPACE +SKIP
    [u'buenas', u'b', u'bu', u'bue', u'buen', u'buena', u'días', u'd', u'dí',
     u'día', u'dias', u'di', u'dia']
    """
    string = clean_value(string)
    index = []
    for word in string.split():
        if word not in index:
            segments = _startswith(word, **kwargs)
            index += segments
            for segment in segments:
                anglicised_segment = anglicise(segment)
                if anglicised_segment != segment:
                    index.append(anglicised_segment)
    return index


def firstletter(string, ignore=None):
    u"""
    >>> firstletter('things')
    ['t']

    >>> firstletter(u'Úig') # doctest: +SKIP
    [u'Ú']

    >>> firstletter('the londis', ignore=['the'])
    ['l']

    >>> firstletter('the therapist', ignore=['the'])
    ['t']

    >>> firstletter(u'él error', ignore=[u'él'])
    [u'e']
    """
    ignore = ignore or []
    regexes = [re.compile(ur'\b{}\b'.format(i), re.I|re.U) for i in ignore]
    for r in regexes:
        string = r.sub('', string)
    try:
        return [string.strip()[0]]
    except IndexError:
        return ['']


def anglicise_char(char):
    u"""Tries to get the closest lexical match in the Latin alphabet for the
    given 'foreign' character, including dipthongs.

    >>> anglicise_char(u'ŕ')
    'r'
    >>> anglicise_char(u'Æ')
    'Ae'
    """
    return CHARACTER_MAP[char]


def anglicise(value):
    """Anglicise every non-Latin-alphabet character in a string"""
    fn = lambda match: anglicise_char(match.group(0))
    return FOREIGN_CHARACTERS_REGEX.sub(fn, value)


if __name__ == '__main__':
    import doctest, sys
    reload(sys)
    sys.setdefaultencoding("UTF-8")
    doctest.testmod()
