import re

from .errors import FieldLookupError, BadValueError

FORBIDDEN_VALUE_REGEX = re.compile(ur'([^_.@ \w-]+)', re.UNICODE)


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
        'contains': u'%s:(%s)',
        'exact': u'%s:"%s"',
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

    def get_value(self):
        return self.__unicode__()

    def __unicode__(self):
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
        children = kwargs.items()

        self.children = []
        for k, v in children:
            try:
                v_is_list = bool(iter(v)) and not issubclass(type(v), basestring)
            except TypeError:
                v_is_list = False

            if v_is_list:
                q = Q(**{k:v[0]})
                for value in v[1:]:
                    q |= Q(**{k:value})
                self.children.append(q)
            else:
                self.children.append((k, v))

        self.conn = self.DEFAULT
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
        return tmpl % (u' %s ' % self.conn).join([str(c) for c in self.children])

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
        map(unicode.lower, [self.NOT, self.AND, self.OR, self.conn])

    def __undebug(self):
        """Undo `__debug()`"""
        for c in self.children:
            getattr(c, '_%s__undebug' % c.__class__.__name__)()
        map(unicode.upper, [self.NOT, self.AND, self.OR, self.conn])

    def _combine(self, other, conn):
        """Return a new Q object with `self` and `other` as children joined
        by `conn`.
        """
        obj = type(self)()
        obj.add(self)
        obj.add(other)
        obj.conn = conn
        return obj
    
    def add(self, child):
        self.children.append(child)

    def get_filters(self):
        filters = []
        for q in self.children:
            if type(q) == Q:
                filters.extend(q.get_filters())
            else:
                filters.append(q)
        return filters


class Query(object):
    """Represents a search API query language string.

    >>> query = Query()
    >>> query.add_keywords('hello I am things')
    >>> query.add_q(Q(things__lte=3))
    >>> unicode(q)
    'hello I am things AND (things <= 3)'
    """
    AND = 'AND'
    OR = 'OR'
    NOT = 'NOT'

    def __init__(self, document_class):
        self.document_class = document_class
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
        effectively adding a filter clause to the querystring.
        """
        if self._gathered_q is None:
            self._gathered_q = q
            return self
        conn = self._gathered_q.DEFAULT.lower()
        self._gathered_q = getattr(self._gathered_q, '__%s__' % conn)(q)
        return self

    def add_keywords(self, keywords):
        """Add keywords to the querystring"""
        self._keywords.append(keywords)
        return self

    def get_filters(self):
        if self._gathered_q:
            return self._gathered_q.get_filters()
        return []

    def get_keywords(self):
        return self._keywords

    def unparse_filter(self, child):
        """Unparse a `Q` object or tuple of the form `(field_lookup, value)`
        into the filters it represents. E.g.:

        >>> q = Q(title__contains="die hard") & Q(rating__gte=7)
        >>> query = Query(FilmDocument)
        >>> query.unparse(q)
        "((title:'die hard') AND (rating >= 7))"
        """
        # If we have a `Q` object, recursively unparse its children
        if isinstance(child, Q):
            tmpl = u'(%s)'
            if child.inverted:
                tmpl = u'%s (%s)' % (child.NOT, '%s')

            conn = u' %s ' % child.conn
            return tmpl % (
                conn.join([self.unparse_filter(c) for c in child.children])
            )

        if child is None:
            return None
        # `child` is a tuple of the form `(field__lookup, value)`

        # TODO: Move this checking to SearchQuery.filter

        filter_lookup, value = child
        expr = FilterExpr(*child)
        # Get the field name to lookup without any comparison operators that
        # might be present in the field name string
        fname = expr._split_filter(filter_lookup)[0]
        doc_fields = self.document_class._meta.fields

        # Can't filter on fields not in the document's fields
        if fname not in doc_fields:
            raise FieldLookupError(u'Prop name %s not in the field list for %s'
                % (fname, self.document_class.__name__))

        field = doc_fields[fname]
        try:
            value = field.prep_value_for_filter(value)
        except (TypeError, ValueError):
            raise BadValueError(u'Value %s invalid for filtering on %s.%s (a %s)'
                % (value, self.document_class.__name__, fname, type(field)))
        # Create a new filter expression with the old filter lookup but with
        # the newly converted value
        return unicode(FilterExpr(filter_lookup, value).get_value())

    def build_filters(self):
        """Get the search API querystring representation for all gathered
        filters so far, ready for passing to the search API.
        """
        return self.unparse_filter(self._gathered_q)

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
            return u'%s %s %s' % (keywords, self.AND, filters)
        if filters:
            return filters
        if keywords:
            return keywords
        return u''
