from google.appengine.api import search as search_api

from .errors import DocumentClassRequiredError
from .fields import (
    TextField,
    IntegerField,
    FloatField,
    DateField,
    Field,
    BooleanField,
    HtmlField,
    AtomField,
    GeoField
)
from .query import SearchQuery, construct_document


class Options(object):
    """Similar to Django's Options class, holds metadata about a class with
    `__metaclass__ = MetaClass`.
    """
    def __init__(self, fields):
        self.fields = fields


class MetaClass(type):
    """Allows the typical declarative class pattern:

    >>> class Thing(search.Document):
    ...     prop = search.Field()
    ...
    >>> t = Thing()
    >>> t.prop = 'hello'
    >>> t.prop
    'Hello'
    >>> Thing.prop
    Traceback ...:
        ...
    AttributeError: type object 'Thing' has no attribute 'prop'
    >>> Thing._meta.fields['prop']
    <search.Field object at 0xXXXXXXXX>
    """
    def __new__(cls, name, bases, dct):
        new_cls = super(MetaClass, cls).__new__(cls, name, bases, dct)

        fields = {}

        # Custom inheritance -- delicious _and_ necessary!
        try:
            parents = [b for b in bases if issubclass (b, DocumentModel)]

            # Reversing simulates the usual MRO
            parents.reverse()

            for p in parents:
                parent_fields = getattr(getattr(p, '_meta', None), 'fields', None)

                if parent_fields:
                    fields.update(parent_fields)
        except NameError:
            pass

        # If there are any search fields defined on the class, allow them to
        # to set themselves up, given that we now know the name of the field
        # instance
        for name, field in dct.items():
            if isinstance(field, Field):
                field.add_to_class(new_cls, name)
                fields[name] = field
                delattr(new_cls, name)

        new_cls._meta = Options(fields)
        return new_cls


class DocumentModel(object):
    """Base class for documents added to search indexes"""

    __metaclass__ = MetaClass

    def __init__(self, **kwargs):
        # No fancy Django `*args` mangling here, just use `**kwargs`
        for name, field in self._meta.fields.items():
            val = kwargs.pop(name, None)
            setattr(self, name, val)

        self.doc_id = unicode(kwargs.get('doc_id', '')).encode('utf-8') or None
        # TODO: Stop this potentially colliding with a defined field name and/or
        # define a nicer API for setting the value
        self._rank = kwargs.get("_rank")

    def __getattribute__(self, name):
        """Make sure that any attribute accessed on document classes returns the
        python representation of its value.
        """
        # TODO: Probably use `Field`s as descriptors and leave this to them
        val = object.__getattribute__(self, name)
        meta = object.__getattribute__(self, '_meta')
        if name in meta.fields:
            f = meta.fields[name]
            val = f.to_python(val)
        return val

    def __setattr__(self, name, val):
        """Make sure that any attibutes set on document class instances get the
        value converted to the search API accepted value.
        """
        # TODO: Probably use `Field`s as descriptors and leave this to them
        if name in self._meta.fields:
            f = self._meta.fields[name]
            val = f.to_search_value(val)
        super(DocumentModel, self).__setattr__(name, val)

    def get_snippets(self):
        """Get the snippets for this document as a dictionary of the form:

            {"field_name": "snippet for this field, if there is one"}

        Returns an empty dict if this document hasn't been returned as part of
        a search query (since it can only be populated then.)
        """
        return {}

    def snippet_or_value(self):
        """Goes through each of this document's snippeted fields and constructs
        a dictionary where each field name points either to the snippet for
        that field if there is one, or just the plain value for that field on
        the document.
        """
        if not hasattr(self, "_snippets_or_values"):
            snippets = self.get_snippets()
            self._snippets_or_values = {
                field: snippets.get(field) or getattr(self, field, None)
                for field in self._meta.fields
            }
        return self._snippets_or_values


class Index(object):
    """A search index. Provides methods for adding, removing and searching
    documents in this index.
    """

    FIELD_MAP = {
        TextField: search_api.TextField,
        HtmlField: search_api.HtmlField,
        IntegerField: search_api.NumberField,
        FloatField: search_api.NumberField,
        DateField: search_api.DateField,
        BooleanField: search_api.NumberField,
        AtomField: search_api.AtomField,
        GeoField: search_api.GeoField
    }

    def __init__(self, name=None, document_class=None):
        # Mandatory keyword argument... right. Mainly for compatibility with
        # the Search API's `Index` class
        if not name:
            raise ValueError('An index must have a non empty name')

        if name.startswith("!") or " " in name:
            raise ValueError("Index names can't start with a '!' or contain spaces")

        self.name = name
        self.document_class = document_class

        # The actual index object from the Search API
        self._index = search_api.Index(name=name)

    def list_documents(self, **kwargs):
        """Deprecated. Use `get_range` instead"""
        return self.get_range(**kwargs)

    def add(self, documents):
        """Deprecated. Use `put` instead"""
        return self.put(documents)

    def remove(self, doc_ids):
        """Deprecated. Use `delete` instead"""
        return self.delete(doc_ids)

    def get_range(self, document_class=None, **kwargs):
        """Get a list of documents from the Search API without actually doing
        a search.

        Takes all the same kwargs that the Search API's get_range takes, plus a
        `document_class` arg for which to construct document objects. If it's
        omitted, the documents are returned as they would be normally from the
        Search API.
        """
        ids_only = kwargs.get("ids_only")
        docs = self._index.get_range(**kwargs)
        document_class = document_class or self.document_class

        if ids_only:
            # This goes against the Search API's return value for `ids_only`,
            # where it returns a list of documents where each object only has
            # its `doc_id` attr available. Returning JUST a list of IDs here
            # keeps compatibility with the `query.SearchQuery`'s `ids_only`
            # behaviour
            return [doc.doc_id for doc in docs]
        if document_class:
            return [construct_document(document_class, doc) for doc in docs]
        return docs

    def get(self, doc_id, document_class=None):
        """Get a document from this index by its ID. It'll be returned as an
        instance of the given `document_class`. Returns `None` if there's no
        document by that ID.
        """
        doc = self._index.get(doc_id)
        document_class = document_class or self.document_class
        if doc and document_class:
            return construct_document(document_class, doc)
        return doc

    def put(self, documents):
        """Add `documents` to this index"""

        def get_fields(d):
            """Convenience function for getting the search API fields list
            from the given document `d`.
            """
            field = lambda f, n, v: self.FIELD_MAP[type(f)](name=n, value=v)
            return [
                field(f, n, f.to_search_value(getattr(d, n, None)))
                for n, f in d._meta.fields.items()
            ]

        # If documents is actually just a single document, stick it in a list
        try:
            len(documents)
        except TypeError:
            documents = [documents]

        # Construct the actual search API documents to add to the underlying
        # search API index
        search_docs = [
            search_api.Document(
                doc_id=d.doc_id,
                rank=d._rank,
                fields=get_fields(d)
            )
            for d in documents
        ]
        return self._index.put(search_docs)

    def delete(self, doc_ids):
        """Delete documents with the given `doc_ids` from this index"""
        return self._index.delete(doc_ids)

    def purge(self):
        """Deletes all documents from this index.

        Probably don't use this on production unless the index only holds
        a really small number of documents. Use App Engine's tasks to delete
        documents in batches instead.
        """
        doc_ids = self.get_range(ids_only=True)
        while doc_ids:
            self.delete(doc_ids)
            doc_ids = self.get_range(
                ids_only=True,
                start_id=doc_ids[-1],
                include_start_object=False
            )

    def search(self, document_class=None, ids_only=False):
        """Initialise the search query for this index and document class"""
        document_class = document_class or self.document_class
        if not document_class:
            raise DocumentClassRequiredError(
                u"A document class must be provided to instantiate with query "
                "results. Either instantiate the index object with one, or "
                "pass one to the search method."
            )

        return SearchQuery(
            self._index,
            document_class=document_class,
            ids_only=ids_only
        )
