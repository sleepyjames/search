import unittest
from django.db import models
from djangae.test import TestCase

from ..adapters import SearchQueryAdapter
from .models import Foo, FooWithMeta


class TestSearchQueryAdapter(TestCase):
    def assertSearchHasSameResult(self, qs, expected_count=None):
        search_qs = SearchQueryAdapter.from_queryset(qs)

        self.assertSameList(qs, search_qs)

        if expected_count is not None:
            self.assertEqual(expected_count, search_qs.count())

    def assertSameList(self, django_qs, search_qs, ordered=False):
        django_ids = [obj.pk for obj in django_qs]

        search_qs = list(search_qs)
        if search_qs and isinstance(search_qs[0], models.Model):
            search_ids = [obj.pk for obj in search_qs]
        else:
            search_ids = [long(doc.doc_id) for doc in search_qs]

        if not ordered:
            django_ids, search_ids = set(django_ids), set(search_ids)
        self.assertEqual(django_ids, search_ids)

    def test_single_filter(self):
        Foo.objects.create(name='David')
        Foo.objects.create(name='Bill')
        qs = Foo.objects.filter(name='David')
        self.assertSearchHasSameResult(qs)

    def test_or(self):
        for name in ['Tom', 'John', 'Joan']:
            Foo.objects.create(name=name)

        qs = Foo.objects.filter(name='Tom') | Foo.objects.filter(name='Joan')
        self.assertSearchHasSameResult(qs)

    def test_search(self):
        FooWithMeta.objects.create(name='Donald Duck')
        FooWithMeta.objects.create(name='Duck')

        search_qs = SearchQueryAdapter.from_queryset(FooWithMeta.objects.all())
        search_qs = search_qs.filter(corpus__contains="don")

        self.assertEqual(1, search_qs.count())

        # exact match
        search_qs = SearchQueryAdapter.from_queryset(FooWithMeta.objects.all())
        search_qs = search_qs.filter(corpus="donald duck")

        self.assertEqual(1, search_qs.count())

    def test_order(self):
        FooWithMeta.objects.create(name='Carla')
        FooWithMeta.objects.create(name='Angus')
        FooWithMeta.objects.create(name='Barbara')

        qs = FooWithMeta.objects.all()
        search_qs = SearchQueryAdapter.from_queryset(qs)

        qs = qs.order_by('-name')
        search_qs = search_qs.order_by('-name')

        self.assertSameList(qs, search_qs.as_model_objects(), ordered=True)

    def test_keywords(self):
        Foo.objects.create(name='David')
        Foo.objects.create(name='Bill')

        qs = Foo.objects.all()
        search_qs = SearchQueryAdapter.from_queryset(qs).keywords("Bill")

        self.assertEqual(1, search_qs.count())

    @unittest.skip("TODO")
    def test_ordering_copied(self):
        asc_qs = FooWithMeta.objects.order_by('name')
        asc_search_qs = SearchQueryAdapter.from_queryset(asc_qs)

        self.assertSameList(asc_qs, asc_search_qs.as_model_objects(), ordered=True)

        desc_qs = FooWithMeta.objects.order_by('-name')
        desc_search_qs = SearchQueryAdapter.from_queryset(asc_qs)
        self.assertSameList(desc_qs, desc_search_qs.as_model_objects(), ordered=True)
