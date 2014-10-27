import re

from google.appengine.api import search as search_api

from . import ql
from .fields import NOT_SET
from .indexers import PUNCTUATION_REGEX


def quote_if_special_characters(value):
    if PUNCTUATION_REGEX.match(value):
        return '"{}"'.format(value)
    return value


def clean_snippet(snippet_value):
    """Only return the snippet value if it looks like there is a match in the
    snippet.
    """
    # Snippets are always returned from the search API, regardless of whether
    # they match the query or not, so the only way to tell if they matched is
    # ...to look for the "<b>" tags that wrap the matched terms. This is pretty
    # rudimentary and probably won't survive future Search API updates.
    if not "<b>" in snippet_value:
        return None
    else:
        # If the text has been snippeted, if there are no ellipses at the end
        # of the string, the search API adds a superfluous '.' to the end, so
        # strip that here. Not sure if it does this when there's already a '.'
        # at the end but...
        if snippet_value.endswith(".") and not snippet_value.endswith("..."):
            snippet_value = snippet_value[:-1]
    return snippet_value


def construct_document(document_class, document):
    """Construct a document object of type `document_class` from `document`, a
    document returned from an App Engine Search API query.

    This sets all the correct values for the fields on the new document and
    annotates it with a function `get_snippets` that returns a list of
    expressions returned for the original document.

    TODO: Make all expressions available (not just snippets).
    """
    fields = document_class._meta.fields
    doc = document_class(doc_id=document.doc_id)

    values = {}
    for f in document.fields:
        if f.name in doc._meta.fields:
            value = fields[f.name].prep_value_from_search(f.value)
            setattr(doc, f.name, value)
            values[f.name] = value

    snippets = {}
    for expr in document.expressions:
        # Only add the snippet if the document has a value for that field
        # (otherwise some snippets come back as '__NONE__', etc.)
        if values.get(expr.name):
            snippets[expr.name] = clean_snippet(expr.value)
        else:
            snippets[expr.name] = None

    # This is hacky as hell - TODO: Make this a proper thing
    def get_snippets():
        return snippets
    doc.get_snippets = get_snippets

    return doc


class SearchQuery(object):
    """Represents a search query for the search API.

    Provides a convenient interface for building up a query string using
    syntax similar to Django's:
   
    >>> i = Index('films')
    >>> q = SearchQuery(i).keywords('bruce willis').filter(genre='action')
    >>> for doc in q[:20]:
    ...     print doc
    <FilmDocument object at 0xXXXXXXXXXX>
    >>> q.count()
    1
    """

    MAX_LIMIT = 1000
    MAX_OFFSET = 1000

    ASC = search_api.SortExpression.ASCENDING
    DESC = search_api.SortExpression.DESCENDING

    def __init__(self, index, document_class=None, ids_only=False):
        """Arguments:

            * index: The Google search API index object to act on.
            * document_class: A subclass of DocumentModel to instantiate with
                from search results.
            * ids_only: Whether or not this query should return only the IDs of
                the documents found, or the full documents themselves.
        """
        self.index = index
        self.document_class = document_class
        self.ids_only = ids_only

        # Actual search query string
        self.query = ql.Query(self.document_class)

        # Query option stuff
        self._cursor = None
        self._next_cursor = None
        self._has_set_limits = False

        self._sorts = []
        self._match_scorer = None

        self._snippeted_fields = []
        self._returned_expressions = []

        self._offset = 0
        self._limit = self.MAX_LIMIT

        # Results
        self._iter = None
        self._number_found = None
        self._results_cache = None
        self._results_response = None

        # XXX: raw query
        self._raw_query = None

    def __nonzero__(self):
        return bool(self.query)

    def __len__(self):
        if self._number_found is None:
            if not self._has_set_limits:
                self._set_limits(0, 1)
            self._run_query()
            self._reset_limits()
        return self._number_found

    def __iter__(self):
        if self._results_cache is None:
            self._results_cache = []
            return self._results_iter()
        return iter(self._results_cache)

    def __getitem__(self, s):
        if isinstance(s, slice):
            if s.start is not None:
                if s.start < 0:
                    raise IndexError("Offset cannot be less than 0")
                if s.start > self.MAX_OFFSET:
                    raise IndexError("Offset cannot be larger than %s" % self.MAX_OFFSET)
            if s.stop is not None:
                if s.stop < (s.start or 0):
                    raise IndexError("Negative indexing not supported")
                if s.stop - (s.start or 0) > self.MAX_LIMIT:
                    raise IndexError("Slice is too large, it must be smaller than %s" % self.MAX_LIMIT)
        else:
            if s > self.MAX_OFFSET:
                raise IndexError("Cannot index higher than %s" % self.MAX_OFFSET)
            if s < 0:
                raise IndexError("Negative indexing not supported")

        new_query = self._clone()
        if isinstance(s, slice):
            new_query._set_limits(s.start, s.stop)
            return new_query if not s.step else list(new_query)[::s.step]
        else:
            new_query._set_limits(s, s+1)
            return list(new_query)[0]

    def _clone(self):
        new_query = type(self)(
            self.index,
            document_class=self.document_class,
            ids_only=self.ids_only
        )
        new_query._set_limits(self._offset, self._limit-self._offset)
        new_query._cursor = self._cursor
        new_query._next_cursor = self._next_cursor
        new_query._sorts = self._sorts
        new_query._snippeted_fields = self._snippeted_fields
        new_query._returned_expressions = self._returned_expressions
        new_query.query = self.query

        # XXX: Copy raw query in clone
        new_query._raw_query = self._raw_query

        return new_query

    def _results_iter(self):
        if self._results_response is None:
            self._run_query()

        if self.ids_only:
            for d in self._results_response:
                self._results_cache.append(d.doc_id)
                yield d.doc_id
        else:
            for d in self._results_response:
                doc = construct_document(self.document_class, d)
                self._results_cache.append(doc)
                yield doc

    def _fill_cache(self, how_many):
        for i in range(how_many):
            try:
                self._results_iter().next()
            except StopIteration:
                break

    def _set_limits(self, low, high):
        low = low or 0
        high = high or self.MAX_LIMIT + low

        self._offset = low
        self._limit = high - low
        self._has_set_limits = True

    def _reset_limits(self):
        self._offset = 0
        self._limit = self.MAX_LIMIT
        self._has_set_limits = False

    def count(self):
        return len(self)

    def filter(self, *args, **kwargs):
        """Add a filter constraint to the query from the `(prop name, value)`
        pairs in kwargs, similar to Django syntax:
        """
        # *args are `Q` objects
        for q in args:
            self.query.add_q(q)
        if kwargs:
            self.query.add_q(ql.Q(**kwargs))
        return self

    def order_by(self, *fields):
        document_fields = self.document_class._meta.fields

        for expr in fields:
            if expr[0] == '-':
                direction = self.DESC
                expression = expr[1:]
            else:
                direction = self.ASC
                expression = expr

            if expression not in document_fields:
                continue

            field = document_fields[expression]
            default_value = (field.default if field.default is not NOT_SET
                else field.none_value())
            self._sorts.append(
                search_api.SortExpression(
                    expression=expression,
                    default_value=default_value,
                    direction=direction
                )
            )
        return self

    def keywords(self, keywords):
        self.query.add_keywords(quote_if_special_characters(keywords))
        return self

    def raw(self, query_string):
        """Execute a raw query directly. This will overwrite any filters or
        keywords previously added to the query, but keep sorting, snippeting,
        etc.
        """
        self._raw_query = query_string
        return self

    def score_with(self, match_scorer):
        """Add a Search API scorer to this query"""
        self._match_scorer = match_scorer
        return self

    def snippet(self, *fields):
        """Add fields to get snippets for when this query is run"""
        for field_name in fields:
            if field_name not in self.document_class._meta.fields:
                raise ValueError(
                    "Can't snippet field {} since {} has no field by that name"
                    .format(field_name, self.document_class.__name__)
                )
        self._snippeted_fields.extend(fields)
        return self

    def add_expression(self, name, expression):
        expr = search_api.FieldExpression(name=name, expression=expression)
        self._returned_expressions.append(expr)
        return self

    def get_snippet_words(self):
        """Get the words in the query that should be used for getting snippets
        from the Search API.

        This makes assumptions (probably wrong ones) about what the desired
        snippeting behaviour. It's unclear exactly how the Search API tries to
        produce snippets for a query like:

            some keywords corpus:"something specific to corpus"

        It seems to work as 'expected' for the plain keywords since they come
        back highlighted in the returned snippet. What it does for the filter
        keywords is difficult to figure out, but they don't appear to be
        highlighted anywhere in any snippets (instead, the ellipsis on the end
        of the snippet seems always to be highlighted).

        To 'fix' this, this method strips out all the string values for any
        filters in the query so that they can be used as the pseudo query to
        snippet for. This means that the words "something specific to corpus"
        do come back highlighted if they're present in any of the fields being
        snippeted.
        """
        snippet_words = [
            v for k, v in self.query.get_filters()
            if isinstance(v, basestring)
        ]
        snippet_words += self.query.get_keywords()
        # If someone quotes a seach query the snippeting will break, so we
        # have to strip them here
        snippet_words = [w.strip('"') for w in snippet_words]
        return u" ".join(snippet_words)

    def get_snippet_expressions(self, snippet_words):
        """Construct the `FieldExpression` objects for the fields that should
        be snippeted when this query is run.
        """
        field_expressions = []
        for field in self._snippeted_fields:
            expression = u'snippet("{}", {})'.format(snippet_words, field)
            field_expressions.append(
                search_api.FieldExpression(name=field, expression=expression)
            )
        return field_expressions

    def _run_query(self):
        offset = self._offset
        limit = self._limit
        sort_expressions = self._sorts

        if self._raw_query is not None:
            query_string = self._raw_query
        else:
            query_string = str(self.query)

        kwargs = {
            "expressions": sort_expressions
        }
        if self._match_scorer:
            kwargs["match_scorer"] = self._match_scorer

        snippet_words = self.get_snippet_words()
        field_expressions = self.get_snippet_expressions(snippet_words)

        sort_options = search_api.SortOptions(**kwargs)
        search_options = search_api.QueryOptions(
            offset=offset,
            limit=limit,
            sort_options=sort_options,
            ids_only=self.ids_only,
            number_found_accuracy=100,
            returned_expressions=field_expressions,
        )
        search_query = search_api.Query(
            query_string=query_string,
            options=search_options
        )

        self._results_response = self.index.search(search_query)
        self._number_found = self._results_response.number_found
