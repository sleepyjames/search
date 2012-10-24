import re, logging

from google.appengine.api import search as search_api

import ql
from fields import NOT_SET


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

    # These are actually 1000 in 1.6.6's search API
    MAX_LIMIT = 500
    MAX_OFFSET = 800

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

        self._offset = 0
        self._limit = self.MAX_LIMIT

        # Results
        self._iter = None
        self._number_found = None
        self._results_cache = None
        self._results_response = None

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
        new_query.query = self.query
        return new_query

    def _results_iter(self):
        if self._results_response is None:
            self._run_query()

        if self.ids_only:
            for d in self._results_response:
                yield d.doc_id
        else:
            fields = self.document_class._meta.fields
            for d in self._results_response:
                doc = self.document_class(doc_id=d.doc_id)
                for f in d.fields:
                    if f.name in doc._meta.fields:
                        value = fields[f.name].prep_value_from_search(f.value)
                        setattr(doc, f.name, value)
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
        self.query.add_keywords(keywords)
        return self

    def _run_query(self):
        offset = self._offset
        limit = self._limit
        sort_expressions = self._sorts
        query_string = str(self.query)

        sort_options = search_api.SortOptions(expressions=sort_expressions)
        search_options = search_api.QueryOptions(
            offset=offset,
            limit=limit,
            sort_options=sort_options,
            ids_only=self.ids_only,
            number_found_accuracy=100
        )
        search_query = search_api.Query(
            query_string=query_string,
            options=search_options
        )

        self._results_response = self.index.search(search_query)
        self._number_found = self._results_response.number_found
