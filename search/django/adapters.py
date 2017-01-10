import operator

from django.db.models import Q as DjangoQ
from django.db.models.lookups import Lookup

from ..ql import Q as SearchQ


def resolve_filter_value(v):
    """Resolve a filter value to one that the search API can handle

    We can't pass model instances for example.
    """
    return getattr(v, 'pk', v)


class SearchQueryAdapter(object):
    """Adapter class to wrap a `search.query.SearchQuery` instance to behaves
    like a Django queryset.

    We only implement 'enough' to allow it's use within a rest_framework
    viewset and django_filter Filterset.
    """
    def __init__(self, query=None, model=None, queryset=None, _is_none=False, ids_only=False):
        self._is_none = _is_none
        self._query = query
        self._queryset = queryset
        self.ids_only = ids_only
        self.model = None if queryset is None else queryset.model

    @classmethod
    def from_queryset(cls, queryset, ids_only=False):
        """Construct a query adapter from a Django queryset"""

        if isinstance(queryset, cls):
            return queryset

        filters = cls.get_filters_from_queryset(queryset)
        search_query = cls.filters_to_search_query(
            filters,
            queryset.model,
            ids_only=ids_only
        )
        return cls(search_query, queryset=queryset, ids_only=ids_only)

    @classmethod
    def filters_to_search_query(cls, filters, model, query=None, ids_only=False):
        """Convert a list of nested lookups filters (a result of
        get_filters_from_queryset) into a SearchQuery objects.
        """
        from .utils import get_search_query

        search_query = query or get_search_query(model, ids_only=ids_only)
        connector = filters['connector']
        children = filters['children']

        q_objects = None

        for child in children:
            if isinstance(child, tuple):
                q = SearchQ(
                    **{
                        "{}__{}".format(child[0], child[1]): child[2]
                    }
                )
                operator_func = getattr(operator, connector.lower() + '_', 'and_')
                q_objects = operator_func(q_objects, q) if q_objects else q

            else:
                search_query = cls.filters_to_search_query(child, model, query=search_query)

        if q_objects is not None:
            search_query.query.add_q(q_objects, conn=connector.upper())

        return search_query

    @classmethod
    def get_filters_from_queryset(cls, queryset, where_node=None):
        """Translates django queryset filters into a nested dict of tuples

        Example:

        >>> queryset = (
                Profile.objects
                    .filter(given_name='pete')
                    .filter(Q(email='1@thing.com') | Q(email='2@thing.com'))
            )
        >>> get_filters_from_queryset(queryset)
        {
            u'children': [
                (u'given_name', u'exact', 'pete'),
                {
                    u'children': [
                        (u'email', u'exact', '1@thing.com'),
                        (u'email', u'exact', '2@thing.com')
                    ],
                    u'connector': u'OR'
                }
            ],
            u'connector': u'AND'
        }
        """
        where_node = where_node or queryset.query.where
        children = []
        node_filters = {
            u'connector': unicode(where_node.connector),
        }

        for node in where_node.children:
            # Normalize expressions which are an AND with a single child and
            # use the child node as the expression instead. This happens if you
            # add whole querysets together.
            if getattr(node, 'connector', None) == 'AND' and len(node.children) == 1:
                node = node.children[0]

            if isinstance(node, Lookup):  # Lookup
                children.append(cls.normalize_lookup(node))

            else:  # WhereNode
                children.append(
                    cls.get_filters_from_queryset(
                        queryset,
                        node,
                    )
                )

        node_filters[u'children'] = children
        return node_filters

    @classmethod
    def model_q_to_search_q(cls, _q):
        """Transform a `django.db.model.Q` tree to `search.ql.Q` tree.

        TODO: handle negation
        """

        if type(_q) is tuple:
            k, v = _q
            return (k, resolve_filter_value(v))

        if not _q.children:
            return None

        q = SearchQ()
        q.conn = _q.connector
        q.children = filter(
            lambda x: x is not None,
            map(cls. model_q_to_search_q, _q.children)
        )
        q.inverted = _q.negated

        if not q.children:
            return None

        # TODO: handle negation?

        return q


    @classmethod
    def normalize_lookup(cls, node):
        """Converts Django Lookup into a single tuple or a list of tuples if
        the lookup_name is IN

        Example for lookup_name IN and rhs ['1@thing.com', '2@thing.com']:
        {
            u'connector': u'OR',
            u'children': [
                (u'email', u'=', u'1@thing.com'),
                (u'email', u'=', u'2@thing.com')
            ]
        }

        Example for lookup_name that's not IN (exact in this case) and value
        '1@thing.com': (u'email', u'=', u'1@thing.com')
        """
        target = unicode(node.lhs.target.name)
        lookup_name = unicode(node.lookup_name)

        # convert "IN" into a list of "="
        if lookup_name.lower() == u'in':
            return {
                u'connector': u'OR',
                u'children': [
                    (
                        target,
                        u'exact',
                        value,
                    )
                    for value in node.rhs
                ]
            }

        return (
            target,
            lookup_name,
            node.rhs,
        )

    def _clone(self):
        return self.__class__(
            model=self.model,
            queryset=self._queryset,
            _is_none=self._is_none,
            ids_only=self.ids_only
        )

    def _transform_filters(self, *args, **kwargs):
        """Normalize a set of filter kwargs intended for Django queryset to
        those than can be used with a search queryset

        Returns tuple of (args, kwargs) to pass directly to SearchQuery.filter
        """

        _args = [
            self.model_q_to_search_q(_q) if type(_q) is DjangoQ else _q
            for _q in args
        ]
        _kwargs = {k: resolve_filter_value(v) for k, v in kwargs.iteritems()}

        return _args, _kwargs

    def as_model_objects(self):
        """Get the IDs in the order they came back from the search API...
        """
        doc_pks = [int(doc.pk) for doc in self]
        results = list(
            self.model.objects
            .filter(id__in=doc_pks)
            .prefetch_related(*self._queryset._prefetch_related_lookups)
        )

        # Since we do pk__in to get the objects from the datastore, we lose
        # any ordering there was. To recreate it, we have to manually order
        # the list back into whatever order the pks from the search API were in.
        key_func = lambda x: doc_pks.index(x.pk)
        results.sort(key=key_func)

        return results

    def all(self):
        clone = self._clone()
        clone._query = self._query._clone()
        return clone

    def __len__(self):
        return 0 if self._is_none else self._query.__len__()

    def __iter__(self):
        if self._is_none:
            return iter([])
        else:
            return self._query.__iter__()

    def __getitem__(self, s):
        if isinstance(s, slice):
            clone = self._clone()
            clone._query = self._query.__getitem__(s)
            return clone
        else:
            return self._query.__getitem__(s)

    def filter(self, *args, **kwargs):
        args, kwargs = self._transform_filters(*args, **kwargs)
        args = args or []

        clone = self._clone()
        clone._query = self._query.filter(*args, **kwargs)

        return clone

    def none(self):
        clone = self._clone()
        clone._is_none = True
        clone._query = self._query._clone()
        return clone

    def count(self):
        return 0 if self._is_none else len(self._query)

    def order_by(self, *fields):
        qs = self._query.order_by(*fields)
        clone = self._clone()
        clone._query = qs
        return clone

    def keywords(self, query_string):
        qs = self._query.keywords(query_string)
        clone = self._clone()
        clone._query = qs
        return clone
