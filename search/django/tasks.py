import logging

from google.appengine.ext.deferred import defer

from django.apps import apps
from django.conf import settings

from djangae.contrib.mappers.pipes import MapReduceTask

from ..indexes import Index

from .indexes import get_index_for_doc, index_instance
from .registry import registry
from .utils import get_rank


# We can delete up to 200 search documents in one RPC call.
DELETE_BATCH_SIZE = 200

# We can retrive up to 1000 in one call but limit to 500 to match
# datatore __in query limit.
RETRIEVE_BATCH_SIZE = 500


class ReindexMapReduceTask(MapReduceTask):
    target = getattr(settings, 'WORKER_MODULE_NAME', 'worker')

    @staticmethod
    def map(instance, *args, **kwargs):
        indexed = index_instance(instance)
        if indexed:
            logging.info(
                u"Indexed {}: {}".format(type(instance).__name__, instance.pk)
            )
        else:
            logging.info(
                u"Model {} isn't registered as being searchable"
                .format(type(instance).__name__)
            )


def get_models_for_actions(app_label, model_name):
    app_label = app_label and app_label.lower()
    model_name = model_name and model_name.lower()

    def does_match_registered_model(model_and_doc):

        meta = model_and_doc[0]._meta
        return meta.app_label == app_label and meta.model_name == model_name

    all_func = lambda x: True

    items = filter(
        does_match_registered_model if app_label and model_name else all_func,
        registry.iteritems()
    )

    if not len(items):
        logging.warning('No model found for {} {}'.format(app_label, model_name))

    return items


def batch_delete_docs(index, doc_ids, batch_size=None):
    """Batch delete docs incase we happen to have > DELETE_BATCH_SIZE to remove.
    """
    batch_size = batch_size or DELETE_BATCH_SIZE
    delete_rpc_operations = []

    for i in xrange(0, len(doc_ids), batch_size):
        batch = doc_ids[i:i+batch_size]
        # index._index refers the underlying GAE search api index object which
        # exposes the async delete method.
        delete_rpc_operations.append(index._index.delete_async(batch))
        logging.info(u'Removing doc_ids {}.'.format(", ".join(batch)))

    # Not sure we really need to block for the results of the delete operations
    # but just incase..
    for fut in delete_rpc_operations:
        fut.get_result()

    logging.info(u'Removed doc_ids {}.'.format(", ".join(batch)))


def purge_index_for_doc(doc_class, batch_size=None):
    batch_size = batch_size or RETRIEVE_BATCH_SIZE
    index = get_index_for_doc(doc_class)
    doc_ids = index.get_range(limit=batch_size, ids_only=True)

    if doc_ids:
        defer(
            purge_index_for_doc, doc_class,
            batch_size=batch_size,
            _target=settings.WORKER_MODULE_NAME,
        )
        logging.info(u'Defer purge "%s" index for next batch.' % index.name)
        batch_delete_docs(index, doc_ids)
    else:
        logging.info(u'Purge index "%s" complete.' % index.name)


def purge_indexes():
    """Purge all search indexes"""
    for (model, (index_name, doc_cls, rank)) in registry.iteritems():
        defer(
            purge_index_for_doc,
            doc_class=doc_cls,
           _target=settings.WORKER_MODULE_NAME,
        )


def remove_orphaned_docs(app_label=None, model_name=None):
    items = get_models_for_actions(app_label, model_name)

    if not len(items):
        logging.warning('No model found for {} {}'.format(app_label, model_name))

    for model_class, doc_cls in items:
        meta = model_class._meta
        logging.info(
            'Remove orphaned docs for {} {} '
            .format(meta.app_label, meta.model_name)
        )
        defer(
            remove_orphaned_docs_for_app_model,
            meta.app_label,
            meta.model_name,
            _target=settings.WORKER_MODULE_NAME,
        )


def remove_orphaned_docs_for_app_model(app_label, model_name, start_id=None, batch_size=500):
    """Remove any search documents who don't have a matching entity in the
    datastore.

    There's no way to shard this other using the search API's `get_range`
    function. So we just retrive a page at a time and defer the next one
    before running the compare/delete logic.
    """

    model = apps.get_model(app_label, model_name)
    doc = registry.get(model)[1]
    index = get_index_for_doc(doc)
    doc_ids = index.get_range(
        ids_only=True,
        start_id=start_id,
        limit=batch_size,
        include_start_object=False
    )

    if not doc_ids:
        logging.info(
            'Finished deferral of orphaned document removal for {} {} '
            .format(model._meta.app_label, model._meta.model_name)
        )
        return

    # Defer the next batch now.
    defer(
        remove_orphaned_docs_for_app_model,
        app_label,
        model_name,
        start_id=doc_ids[-1],
        batch_size=batch_size,
        _target=settings.WORKER_MODULE_NAME,
    )

    # Document ids are string, pks are longs, so ensure types match.
    pks_from_search = map(long, map(long, doc_ids))
    pks_from_datastore = model.objects.filter(pk__in=pks_from_search).values_list('pk', flat=True)

    orphan_doc_ids = [
        str(pk) for pk in
        set(pks_from_search).difference(pks_from_datastore)
    ]

    if not orphan_doc_ids:
        return

    logging.info(
        'Found {} orphaned search documents for {}'
        .format(orphan_doc_ids, model)
    )

    batch_delete_docs(index, orphan_doc_ids)
