# -*- coding: utf-8 -*-
from django.db.models.signals import post_save, pre_delete

from djangae.test import TestCase

from ... import (
    fields as search_fields,
    indexers as search_indexers
)
from ...query import SearchQuery

from ..adapters import SearchQueryAdapter
from ..registry import registry
from ..utils import (
    disable_indexing,
    get_uid,
    get_search_query,
)

from .models import Foo, FooWithMeta, Related, FooDocument


class TestSearchable(TestCase):

    def test_decorator_side_effects(self):
        # A signal's receiver list is of the form:
        #
        #   `[((dispatch_uid, some_other_id), receiver), ...]`
        #
        # We test against the dispatch_uid since we know what that should be.
        index_receivers = [
            f[1] for f in post_save.receivers
            if f[0][0] == get_uid(Foo, FooDocument, "django_foo")
        ]
        unindex_receivers = [
            f[1] for f in pre_delete.receivers
            if f[0][0] == get_uid(Foo, FooDocument, "django_foo")
        ]

        self.assertEqual(len(index_receivers), 1)
        self.assertEqual(len(unindex_receivers), 1)

    def test_search_query_method(self):
        # Only test you can do here really is that it doesn't error... Should
        # probably test to see that the resulting query is bound to the right
        # index and document class somehow
        query = get_search_query(Foo)
        self.assertEqual(type(query), SearchQuery)

    def test_search_method_on_queryset(self):
        Foo.objects.create(name="Box")
        Foo.objects.create(name="Square")

        search_qs = Foo.objects.filter(name="Box").search()
        self.assertTrue(isinstance(search_qs, SearchQueryAdapter))

        self.assertEqual(1, len(search_qs))


    def test_search_method_on_queryset_with_keywords(self):
        Foo.objects.create(name="Box")
        Foo.objects.create(name="Square")

        search_qs = Foo.objects.all().search(keywords='Box')
        self.assertTrue(isinstance(search_qs, SearchQueryAdapter))

        self.assertEqual(1, len(search_qs))

    def test_index_on_save_of_instance(self):
        related1 = Related.objects.create(name="Book")

        thing1 = Foo.objects.create(
            name="Box",
            is_good=False,
            relation=related1,
            tags=["various", "things"]
        )

        related2 = Related.objects.create(name="Book")
        Foo.objects.create(
            name="Crate",
            is_good=False,
            relation=related2,
            tags=["other", "data"]
        )

        query = get_search_query(Foo).keywords("Box")
        self.assertEqual(query.count(), 1)

        doc = query[0]
        self.assertEqual(doc.doc_id, str(thing1.pk))
        self.assertEqual(doc.pk, str(thing1.pk))
        self.assertEqual(doc.name, "Box")
        self.assertEqual(doc.is_good, False)
        self.assertEqual(doc.relation, str(related1.pk))
        self.assertEqual(doc.tags.split("|"), ["various", "things"])

        # Have to catch an assertion error here that Djangae throws because
        # `Foo` is outside of a registered Django app, so it doesn't know
        # how to uncache it on update. For more info, look at the error.
        try:
            thing1.save()
        except AssertionError:
            pass

        query = get_search_query(Foo).keywords("Box")
        self.assertEqual(query.count(), 1)

    def test_unindex_on_delete_of_instance(self):
        related = Related.objects.create(name="Book")
        thing = Foo.objects.create(
            name="Box",
            is_good=False,
            relation=related,
            tags=["various", "things"]
        )
        query = get_search_query(Foo).keywords("Box")
        self.assertEqual(query.count(), 1)

        # Same as above happens on delete...
        try:
            thing.delete()
        except AssertionError:
            pass

        query = get_search_query(Foo).keywords("Box")
        self.assertEqual(query.count(), 0)

    def test_signals_not_run_when_indexing_disabled(self):
        with disable_indexing():
            related = Related.objects.create(name="Book")
            Foo.objects.create(
                name="Box",
                is_good=False,
                relation=related,
                tags=["various", "things"]
            )

        query = get_search_query(Foo).keywords("Box")
        self.assertEqual(query.count(), 0)


class TestSearchableMeta(TestCase):
    def test_metaclass_side_effects(self):
        index_receivers = [
            f[1] for f in post_save.receivers
            if f[0][0] == get_uid(FooWithMeta, "FooWithMetaDocument", "django_foowithmeta")
        ]
        unindex_receivers = [
            f[1] for f in pre_delete.receivers
            if f[0][0] == get_uid(FooWithMeta, "FooWithMetaDocument", "django_foowithmeta")
        ]

        self.assertEqual(len(index_receivers), 1)
        self.assertEqual(len(unindex_receivers), 1)

    def test_search_query_method(self):
        query = get_search_query(FooWithMeta)
        self.assertEqual(type(query), SearchQuery)

    def test_field_types(self):
        document_meta = registry[FooWithMeta][1]._doc_meta
        self.assertIsInstance(
            document_meta.fields['name'],
            search_fields.TextField
        )

        self.assertIsInstance(
            document_meta.fields['is_good'],
            search_fields.BooleanField
        )

    def test_index(self):
        document_cls = registry[FooWithMeta][1]

        related = Related.objects.create(name=u"Boôk")
        thing1 = FooWithMeta.objects.create(
            name="Big Box",
            is_good=False,
            tags=["various", "things"],
            relation=related
        )

        doc = document_cls(doc_id=str(thing1.pk))
        doc.build_base(thing1)

        self.assertEqual(thing1.name, doc.name)
        self.assertEqual(thing1.name.lower(), doc.name_lower)
        self.assertEqual(thing1.is_good, doc.is_good)
        self.assertEqual(thing1.tags, doc.tags.split("|"))
        self.assertEqual(related.name, related.name)

        corpus = search_indexers.startswith(thing1.name)
        corpus += search_indexers.contains(related.name)
        self.assertEqual(set(corpus), set(doc.corpus.split(' ')))
        self.assertIn(thing1.name, doc.corpus)
        self.assertIn(related.name, doc.corpus)
