import datetime
import unittest

from google.appengine.api import search as search_api

from ..indexes import DocumentModel, Index
from ..fields import TZDateTimeField, TextField
from ..query import SearchQuery
from ..ql import Q
from .. import timezone

from .base import AppengineTestCase


class FakeDocument(DocumentModel):
    foo = TextField()
    created = TZDateTimeField()


class TestSearchQueryClone(unittest.TestCase):
    def test_clone_keywords(self):
        q = SearchQuery("dummy", document_class=FakeDocument).keywords("bar")
        q1 = q.filter(foo="baz")

        self.assertEqual(
            u"bar",
            unicode(q.query)
        )

        self.assertEqual(
            u'bar AND (foo:"baz")',
            unicode(q1.query)
        )

    def test_clone_filters(self):
        q = SearchQuery("dummy", document_class=FakeDocument).filter(
            (Q(foo="bar") | Q(foo="baz")) & ~Q(foo="neg")
        )

        q1 = q.filter(~Q(foo="neg2"))

        self.assertEqual(
            u'(((foo:"bar") OR (foo:"baz")) AND NOT (foo:"neg"))',
            unicode(q.query)
        )

        self.assertEqual(
            u'('
            '(((foo:"bar") OR (foo:"baz")) AND NOT (foo:"neg")) '
            'AND NOT (foo:"neg2")'
            ')',
            unicode(q1.query)
        )


class TestSearchQueryFilter(unittest.TestCase):
    def test_filter_on_datetime_field(self):
        xmas = datetime.datetime(2016, 12, 31, 12, tzinfo=timezone.utc)
        q = SearchQuery('dummy', document_class=FakeDocument)
        q = q.filter(created__gt=xmas)

        self.assertEqual(unicode(q.query), u'(created > 1483185600)')


class TestCursor(AppengineTestCase):
    def test_cursor(self):
        idx = Index('dummy', FakeDocument)
        idx.put(FakeDocument(foo='thing'))
        idx.put(FakeDocument(foo='thing2'))

        idx.get_range()
        q = idx.search().set_cursor().order_by('foo')[:1]
        list(q)

        self.assertTrue(q.next_cursor)

        q2 = idx.search().set_cursor(cursor=q.next_cursor).order_by('foo')
        self.assertEqual(2, len(q2)) # still returns full count
        results = list(q2)
        self.assertEqual(1, len(results)) # but only one document
        self.assertEqual('thing2', results[0].foo)
        self.assertFalse(q2.next_cursor)
