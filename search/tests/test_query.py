import datetime
import unittest

from search.indexes import DocumentModel
from search.fields import TZDateTimeField, TextField
from search.query import SearchQuery
from search.ql import Q
from search import timezone


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
