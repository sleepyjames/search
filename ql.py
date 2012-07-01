import re, logging

FORBIDDEN_VALUE_REGEX = re.compile(ur'([^.@ \w-]+)', re.UNICODE)


class FilterExpr(object):
    # Default separator between field name and lookup type in the left hand
    # side of the filter expression
    SEPARATOR = '__'
    # If the parsed comparision operator type from the left hand side of the
    # filter expression is invalid, fall back to this
    DEFAULT_OP = 'exact'
    # Only these values are valid after `SEPARATOR` in property names. Each
    # comparison operator string is mapped to its equivalent query syntax
    # template
    OPS = {
        'contains': u'%s:"%s"',
        'exact': u'%s = %s',
        'lt': u'%s < %s',
        'lte': u'%s <= %s',
        'gt': u'%s > %s',
        'gte': u'%s >= %s',
    }

    def __init__(self, k, v, valid_ops=None):
        self.prop_name, self.value = k, v
        self.valid_ops = valid_ops or self.OPS

    def __str__(self):
        """`str()`ing a `FilterExpr` returns the string for this filter
        formatted in the search API syntax.
        """
        prop_name, op = self._split_filter(self.prop_name)
        template = self.OPS[op]
        return template % (prop_name, self.value)
    
    def __debug(self):
        """Enable debugging features"""
        # This is handy for testing: see Q.__debug for why
        self.OPS['is'] = ('%s == %s')

    def __undebug(self):
        if 'is' in self.OPS:
            del self.OPS['is']
    
    def _split_filter(self, prop_name):
        """Splits `prop_name` by `self.SEPARATOR` and returns the parts,
        with the comparison operator defaulting to a sensible value if it's not
        in `self.OPS` or if it's missing.

        >>> prop_name = 'rating__lte'
        >>> self._split_filter(prop_name)
        ['rating', 'lte']
        >>> prop_name = 'rating'
        >>> self._split_filter(prop_name)
        ['rating', self.DEFAULT_OP]
        """
        op_name = 'exact'
        if self.SEPARATOR in prop_name:
            prop_name, op_name = prop_name.split(self.SEPARATOR)
            if op_name not in self.OPS:
                # XXX: raise an error here?
                op_name = self.DEFAULT_OP
        return [prop_name, op_name]


class Q(object):
    AND = u'AND'
    OR = u'OR'
    NOT = u'NOT'
    DEFAULT = AND

    def __init__(self, **kwargs):
        self.children = [FilterExpr(k, v) for k, v in kwargs.items()]
        self.conj = self.DEFAULT
        self.inverted = False

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __invert__(self):
        obj = type(self)()
        obj.add(self)
        obj.inverted = True
        return obj

    def __str__(self):
        """Recursively stringify this expression and its children."""
        tmpl = u'(%s)'
        if self.inverted:
            # TODO: this is messy, must be some nicer way I can't think of
            tmpl = u' '.join([u'(%s' % self.NOT, u'%s)'])
        return tmpl % (u' %s ' % self.conj).join([str(c) for c in self.children])

    def __debug(self):
        """Enable debugging features. Handy for testing with stuff like:

        >>> q = Q(True__is=True) | Q(True__is=False) & Q(False__is=False)
        >>> q._Q__debug()
        >>> str(q)
        "(True == True) or ((True == False) and (False == False))"
        >>> eval(_) == True
        True
        """
        for c in self.children:
            getattr(c, '_%s__debug' % c.__class__.__name__)()
        map(unicode.lower, [self.NOT, self.AND, self.OR, self.conj])

    def __undebug(self):
        """Undo `__debug()`"""
        for c in self.children:
            getattr(c, '_%s__undebug' % c.__class__.__name__)()
        map(unicode.upper, [self.NOT, self.AND, self.OR, self.conj])

    def _combine(self, other, conj):
        """Return a new Q object with `self` and `other` as children joined
        by `conj`.
        """
        obj = type(self)()
        obj.add(self)
        obj.add(other)
        obj.conj = conj
        return obj
    
    def add(self, child):
        self.children.append(child)


class Query(object):
    """Represents a search API query language string.

    >>> query = Query()
    >>> query.add_keywords('hello I am things')
    >>> query.add_q(Q(things__lte=3))
    >>> unicode(q)
    'hello I am things AND (things <= 3)'
    """
    def __init__(self):
        self._gathered_q = None
        self._keywords = []

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        """This is how we get to the actual underlying querystring"""
        return unicode(self.build_query()).encode('utf-8')

    def _clean(self, value):
        """Remove any punctuation that might break the search API's lexer
        (e.g. '^') from the given value.
        """
        return FORBIDDEN_VALUE_REGEX.sub('', value)

    def add_q(self, q):
        """Add a `Q` object to the internal reduction of gathered Qs,
        effectively adding a filter clause to the querystring."""
        if self._gathered_q is None:
            self._gathered_q = q
            return self
        conj = self._gathered_q.DEFAULT.lower()
        self._gathered_q = getattr(self._gathered_q, '__%s__' % conj)(q)
        return self

    def add_keywords(self, keywords):
        """Add keywords to the querystring"""
        self._keywords.append(keywords)
        return self

    def build_filters(self):
        """Get the search API querystring representation for all gathered
        filters so far, ready for passing to the search API.
        """
        # The Q object knows how to represent itself
        if self._gathered_q is not None:
            return str(self._gathered_q)

    def build_keywords(self):
        """Get the search API querystring representation for the currently
        gathered keywords.
        """
        if self._keywords:
            return self._clean(u' '.join(self._keywords))

    def build_query(self):
        """Build the full querystring"""
        filters = self.build_filters()
        keywords = self.build_keywords()


        if filters and keywords:
            return u'%s AND %s' % (keywords, filters)
        elif filters:
            return filters
        elif keywords:
            return keywords
        return ''
