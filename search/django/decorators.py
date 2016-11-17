from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.module_loading import import_string

from ..indexes import Index

from .adapters import SearchQueryAdapter
from .documents import document_factory
from .indexes import index_instance, unindex_instance
from .registry import registry
from .utils import (
    get_default_index_name,
    get_rank,
    get_uid,
    indexing_is_enabled,
)


def connect_signals(model_class, document_class, index_name, rank=None):
    """Wire up `model_class`'s `post_save` and `post_delete` signals to
    receivers that will index and unindex instances when saved and deleted.

    Args:
        * model_class: The model class to connect signals for
        * document_class: The document class to index instances of
            `model_class` with
        * index_name: The name of the index to put/delete to/from
        * rank: See `searchable`
    """
    uid = get_uid(model_class, document_class, index_name)

    @receiver(post_save, sender=model_class, dispatch_uid=uid, weak=False)
    def index(sender, instance, **kwargs):
        if indexing_is_enabled():
            index_instance(instance)

    @receiver(post_delete, sender=model_class, dispatch_uid=uid, weak=False)
    def unindex(sender, instance, **kwargs):
        if indexing_is_enabled():
            unindex_instance(instance)


def add_search_queryset_method(model_class):
    """Add a `search` method to the model's default manager queryset class"""

    def search(self, keywords=None):
        """Create a search query for this model.

        Returns:
            A search adapter that can be used to filter and keyword search
            objects in this model's index.
        """
        q = SearchQueryAdapter.from_queryset(self)
        return q.keywords(keywords) if keywords else q

    # Add the method to the default manager's queryset as a best guess
    queryset_class = model_class._default_manager._queryset_class

    if not getattr(queryset_class, "search", None):
        queryset_class.search = search


def searchable(
        document_class=None,
        index_name=None,
        rank=None,
        add_default_queryset_search_method=True
    ):
    """Make the decorated model searchable. Can be used to decorate a model
    multiple times should that model need to be indexed in several indexes.

    Adds receivers for the model's `post_save` and `pre_delete` signals that
    index and unindex that instance, respectfully, whenever it's saved or
    deleted.

    Args:
        document_class: The document class to index instances of this model
            with. When indexing an instance, a document class will be
            instantiated and then have its `build` method called, with the
            instance as an argument. If this is not passed then a SearchMeta
            subclass must be defined on the model.
        index_name: The name of the search index to add the documents to. It's
            valid for the same object to be added to multiple indexes.
            Default: lowercase {app_label}_{model_name}.
        rank: Either:

            * The name of a field on the model instance
            * The name of a method taking no args on the model instance
            * A callable taking no args

            that will return the rank to use for that instance's document in
            the search index.
    """
    if document_class and isinstance(document_class, basestring):
        document_class = import_string(document_class)

    def decorator(model_class):
        _document_class = document_class

        if not _document_class:
            _document_class = document_factory(model_class)

        index = Index(index_name or get_default_index_name(model_class))
        connect_signals(model_class, _document_class, index.name, rank=rank)

        if add_default_queryset_search_method:
            add_search_queryset_method(model_class)

        registry[model_class] = (index.name, _document_class, rank)
        return model_class

    return decorator
