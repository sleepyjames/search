# -*- coding: utf-8 -*-

import re, sys, logging

from globs import CHARACTER_MAP, FOREIGN_CHARACTERS_REGEX


log = logging.getLogger(__name__)


OTHER_FIRST_LETTER_STRING = u'zzz'
PUNCTUATION_REGEX = re.compile(ur'[^\w -\'"+]', re.U)
WHITESPACE_REGEX = re.compile(ur'[\s]+', re.U)


def clean_value(value):
    value = value or ''
    value = PUNCTUATION_REGEX.sub(u' ', value)
    value = WHITESPACE_REGEX.sub(u' ', value)
    return value.strip()


def _startswith(string, min_size=0, max_size=sys.maxint):
    """
    >>> _startswith('hello')
    ['hello', 'h', 'he', 'hel', 'hell']

    >>> _startswith('hello words') # doctest: +NORMALIZE_WHITESPACE
    ['hello words', 'h', 'he', 'hel', 'hell', 'hello', 'hello ', 'hello w',
     'hello wo', 'hello wor', 'hello word']

    >>> _startswith('All THE ThinGs') # doctest: +NORMALIZE_WHITESPACE
    ['all the things', 'a', 'al', 'all', 'all ', 'all t', 'all th', 'all the',
     'all the ', 'all the t', 'all the th', 'all the thi', 'all the thin',
     'all the thing']
    """
    vals = []
    if len(string) >= min_size and len(string) <= max_size:
        vals = [string.lower()]

    for i in range(1, len(string)):
        val = string[:i]
        if len(val) < min_size or len(val) > max_size:
            continue
        if val not in vals:
            vals.append(val.lower())
    return vals


def contains(string, **kwargs):
    string = clean_value(string)
    vals = []

    for word in string.split():
        if word not in vals:
            for i in range(len(word)):
                segments = startswith(word[i:], **kwargs)
                vals += segments
    return set(vals)


def startswith(string, **kwargs):
    u"""
    >>> startswith('Plorm Hamdis') # doctest: +NORMALIZE_WHITESPACE
    [u'plorm', u'p', u'pl', u'plo', u'plor', u'hamdis', u'h', u'ha', u'ham',
     u'hamd', u'hamdi']

    The next test is skipped because it breaks for some reason, even though it
    follows the answer here:
    http://stackoverflow.com/questions/1733414/how-do-i-include-unicode-strings-in-python-doctests

    >>> print startswith(u'buenas días') # doctest: +NORMALIZE_WHITESPACE +SKIP
    [u'buenas', u'b', u'bu', u'bue', u'buen', u'buena', u'días', u'd', u'dí',
     u'día', u'dias', u'di', u'dia']
    """
    string = clean_value(string)
    vals = []
    for word in string.split():
        if word not in vals:
            segments = _startswith(word, **kwargs)
            vals += segments
            for segment in segments:
                anglicised_segment = anglicise(segment)
                if anglicised_segment != segment:
                    vals.append(anglicised_segment)
    return vals


def firstletter(string, ignore=None):
    """
    >>> firstletter('things')
    ['t']

    >>> firstletter('the londis', ignore=['the'])
    ['l']

    >>> firstletter('a banana', ignore=['a'])
    ['b']
    """
    def sub_firstletter(value):
        for c in value:
            try:
                return CHARACTER_MAP[c]
            except KeyError:
                if re.match('[a-zA-Z]', c):
                    return c
                else:
                    return OTHER_FIRST_LETTER_STRING
        return value

    ignore = ignore or []
    regexes = [re.compile(i, re.I) for i in ignore]
    for r in regexes:
        string = r.sub('', string)
    return [sub_firstletter(string.strip()).lower()]


def anglicise_char(char_match):
    return CHARACTER_MAP[char_match.group(0)]


def anglicise(value):
    return FOREIGN_CHARACTERS_REGEX.sub(anglicise_char, value)

if __name__ == '__main__':
    import doctest, sys
    reload(sys)
    sys.setdefaultencoding("UTF-8")
    doctest.testmod()
