import logging

from google.appengine.api import modules
from google.appengine.ext import deferred

from django.apps import apps
from django.conf import settings

from djangae.contrib.mappers.pipes import MapReduceTask

from ..indexes import Index

from .indexes import get_index_for_doc, index_instance
from .registry import registry


# We can delete up to 200 search documents in one RPC call.
DELETE_BATCH_SIZE = 200

# We can retrive up to 1000 in one call but limit to 500 to match
# datatore __in query limit.
RETRIEVE_BATCH_SIZE = 500

logger = logging.getLogger(__name__)


def get_deferred_target():
    """Return the name of an App Engine module or version for running a
    deferred task.
    """
    settings_key = 'WORKER_MODULE_NAME'

    if hasattr(settings, settings_key):
        target = getattr(settings, settings_key)
    else:
        target = modules.get_current_version_name()

    return target


class ReindexMapReduceTask(MapReduceTask):
    @property
    def target(self):
        # Wrapped in a property so it doesn't get called when this module is
        # imported (because the modules API will raise KeyError if called too
        # early).
        return get_deferred_target()

    @staticmethod
    def map(instance, *args, **kwargs):
        indexed = index_instance(instance)
        if indexed:
            logger.info(u"Indexed %s: %s", type(instance).__name__, instance.pk)
        else:
            logger.info(
                u"Model %s isn't registered as being searchable", type(instance).__name__
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
        logger.warning('No model found for %s %s', app_label, model_name)

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
        logger.info(u'Removing doc_ids %r', batch)

    # Not sure we really need to block for the results of the delete operations
    # but just incase..
    for fut in delete_rpc_operations:
        fut.get_result()

    logger.info(u'Removed doc_ids %r', batch)


def purge_index_for_model(model, batch_size=None):
    batch_size = batch_size or RETRIEVE_BATCH_SIZE
    search_meta = registry.get(model)
    index_name = search_meta[0]

    index = Index(index_name)
    doc_ids = index.get_range(limit=batch_size, ids_only=True)

    if doc_ids:
        target = get_deferred_target()
        deferred.defer(
            purge_index_for_model, model,
            batch_size=batch_size,
            _target=target,
        )
        logger.info(u'Defer purge %r index for next batch.', index.name)
        batch_delete_docs(index, doc_ids)
    else:
        logger.info(u'Purge index %r complete.', index.name)


def purge_indexes():
    """Purge all search indexes"""
    target = get_deferred_target()

    for model in registry.iterkeys():

        deferred.defer(
            purge_index_for_model,
            model=model,
           _target=target,
        )


def remove_orphaned_docs(app_label=None, model_name=None):
    items = get_models_for_actions(app_label, model_name)
    target = get_deferred_target()

    if not len(items):
        logger.warning('No model found for %s %s', app_label, model_name)

    for model_class, doc_cls in items:
        meta = model_class._meta
        logger.info('Remove orphaned docs for %s %s', meta.app_label, meta.model_name)

        deferred.defer(
            remove_orphaned_docs_for_app_model,
            meta.app_label,
            meta.model_name,
            _target=target,
        )


def remove_orphaned_docs_for_app_model(app_label, model_name, start_id=None, batch_size=500):
    """Remove any search documents who don't have a matching entity in the
    datastore.

    There's no way to shard this other using the search API's `get_range`
    function. So we just retrive a page at a time and defer the next one
    before running the compare/delete logic.
    """

    model = apps.get_model(app_label, model_name)
    search_meta = registry.get(model)
    index_name = search_meta[0]

    index = Index(index_name)
    doc_ids = index.get_range(
        ids_only=True,
        start_id=start_id,
        limit=batch_size,
        include_start_object=False
    )

    if not doc_ids:
        logger.info(
            'Finished deferral of orphaned document removal for %s %s',
            model._meta.app_label,
            model._meta.model_name,
        )
        return

    target = get_deferred_target()
    # Defer the next batch now.
    deferred.defer(
        remove_orphaned_docs_for_app_model,
        app_label,
        model_name,
        start_id=doc_ids[-1],
        batch_size=batch_size,
        _target=target,
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

    logger.info('Found %r orphaned search documents for %s', orphan_doc_ids, model)

    batch_delete_docs(index, orphan_doc_ids)
