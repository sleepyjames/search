import logging
import threading

from django.conf import settings

try:
    from text_unidecode import unidecode
except ImportError:
    HAS_UNIDECODE = False
else:
    HAS_UNIDECODE = True

from .. import fields
from ..indexes import Index

from .registry import registry


status = threading.local()


MAX_RANK = 2 ** 31


def get_ascii_string_rank(string, max_digits=9):
    """Convert a string into a number such that when the numbers are sorted
    they maintain the lexicographic sort order of the words they represent.

    The number of characters in the string for which lexicographic order will
    be maintained depends on max_digits. For the default of 9, the number of
    chars that the order is maintained for is 5.

    Unfortunately this basically means:

    >>> get_ascii_string_rank("Python") == get_ascii_string_rank("Pythonic")
    True

    when obviously it'd be better if the rank for "Pythonic" was > than the
    rank for "Python" since "Pythonic" is alphabetically after "Python".
    """
    # Smallest ordinal value we take into account
    smallest_ord = ord(u"A")
    # Ord value to use for punctuation - we define punctuation as ordering after
    # all letters in the alphabet
    punctuation_ord = smallest_ord - 1
    # Offset to normalize the actual ord value by. 11 is taken off because
    # otherwise the values for words starting with 'A' would start with '00'
    # which would be ignored when cast to an int
    offset = smallest_ord - 11
    # Fn to get the normalized ordinal
    get_ord = lambda c: (ord(c) if c.isalpha() else punctuation_ord) - offset
    # Padding for the string if it's shorter than `max_digits`
    padding = chr(punctuation_ord) * max_digits

    if HAS_UNIDECODE:
        # And parse it with unidecode to get rid of non-ascii characters
        string = unidecode(string)
    else:
        logging.warning(
            'text_unidecode package not found. If a string with non-ascii chars '
            'is used for a document rank it may result in unexpected ordering'
        )

    # Get the ordinals...
    ords = [get_ord(c) for c in (string + padding)]
    # Concat them, making sure they're all 2 digits long
    joinable = [str(o).zfill(2) for o in ords]
    # Cast back to an int, making sure it's at at most `max_digits` long
    return int("".join(joinable)[:max_digits])


def get_rank(instance, rank=None):
    """Get the rank with which this instance should be indexed.

    Args:
        instance: A Django model instance
        rank: Either:

            * The name of a field on the model instance
            * The name of a method taking no args on the model instance
            * A callable taking no args

            that will return the rank to use for that instance's document in
            the search index.

    Returns:
        The rank value, between 0 and 2**63
    """
    desc = True

    if not rank:
        return rank

    if callable(rank):
        rank = rank()
    else:
        desc = rank.startswith("-")
        rank = rank[1:] if desc else rank

        rank = getattr(instance, rank)
        if callable(rank):
            rank = rank()

    if isinstance(rank, basestring):
        rank = get_ascii_string_rank(rank)

    # The Search API returns documents in *descending* rank order by default,
    # so reverse if the rank is to be ascending
    return rank if desc else MAX_RANK - rank


def get_default_index_name(model_class):
    """Get the default search index name for the given model"""
    return "{0.app_label}_{0.model_name}".format(model_class._meta)


def get_uid(model_class, document_class, index_name):
    """Make the `dispatch_uid` for this model, document and index combination.

    Returns:
        A string UID for use as the `dispatch_uid` arg to `@receiver` or
        `signal.connect`
    """
    if not isinstance(model_class, basestring):
        model_class = model_class.__name__

    if not isinstance(document_class, basestring):
        document_class = document_class.__name__

    return "{index_name}.{model_class}.{document_class}".format(
        index_name=index_name,
        model_class=model_class,
        document_class=document_class
    )


def indexing_is_enabled():
    """
    Returns:
        Whether or not search indexing/deleting is enabled.
    """
    default = getattr(
        settings,
        "SEARCH_INDEXING_ENABLED_BY_DEFAULT",
        True
    )
    return getattr(status, "_is_enabled", default)


def _disable():
    """Disable search indexing globally for this thread"""
    status._is_enabled = False


def _enable():
    """Enable the search indexing globally for this thread"""
    status._is_enabled = True


class DisableIndexing(object):
    """A context manager/callable that disables indexing. If used in a `with`
    statement, indexing will be disabled temporarily and then restored to
    whatever state it was before.
    """
    def __enter__(self):
        if not hasattr(self, "previous_state"):
            self.previous_state = indexing_is_enabled()
        _disable()

    def __call__(self):
        self.previous_state = indexing_is_enabled()
        _disable()
        return self

    def __exit__(self, *args, **kwargs):
        _enable() if self.previous_state is True else _disable()


class EnableIndexing(object):
    """A context manager/callable that enables indexing. If used in a `with`
    statement, indexing will be enabled temporarily and then restored to
    whatever state it was before.
    """
    def __enter__(self):
        if not hasattr(self, "previous_state"):
            self.previous_state = indexing_is_enabled()
        _enable()

    def __call__(self):
        self.previous_state = indexing_is_enabled()
        _enable()
        return self

    def __exit__(self, *args, **kwargs):
        _enable() if self.previous_state is True else _disable()


# Context managers for use with the `with` statement, to temporarily disable/
# enable search indexing
disable_indexing = DisableIndexing()
enable_indexing = EnableIndexing()


def get_datetime_field():
    return fields.TZDateTimeField if settings.USE_TZ else fields.DateTimeField


def get_search_query(model_class, ids_only=False):
    """Construct a search query bound to the index and document class registered
    for the given Django model class.

    Args:
        model_class: A Django model class
        ids_only: Whether to only return the IDs from the search query

    Returns:
        A raw search.Query object bound to the default index and document class
        for the given model.
    """
    search_meta = registry.get(model_class)

    if not search_meta:
        raise registry.RegisterError(u"This model isn't registered with @searchable")

    index_name, document_class, _ = search_meta
    index = Index(index_name)
    return index.search(document_class=document_class, ids_only=ids_only)
