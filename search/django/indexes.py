from .registry import registry
from .utils import get_rank

from ..indexes import Index


def get_index_for_doc(document_cls):
    """Return a search index based on a Document class"""
    parts = document_cls.__module__.split('.')
    return Index('_'.join([parts[0], parts[2]]))


def index_instance(instance):
    model = type(instance)
    search_meta = registry.get(model)

    if search_meta:
        index_name, document_class, rank = search_meta
        doc = document_class(
            doc_id=str(instance.pk),
            _rank=get_rank(instance, rank=rank)
        )
        doc.build_base(instance)
        index = Index(index_name)
        index.put(doc)

        return True


def unindex_instance(instance):
    model = type(instance)
    search_meta = registry.get(model)

    if search_meta:
        index_name = search_meta[0]

        index = Index(index_name)
        index.delete(str(instance.pk))
