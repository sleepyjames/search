import unittest

from search.indexes import DocumentModel
from search.fields import TextField
from search.query import SearchQuery
from search.ql import Q

class FakeDocument(DocumentModel):
    foo = TextField()


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
