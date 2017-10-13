import datetime
import unittest

from search.ql import Query, Q, GeoQueryArguments
from search.fields import TextField, GeoField, DateField
from search.indexes import DocumentModel


class FakeDocument(DocumentModel):
    foo = TextField()
    bar = DateField()


class FakeGeoDocument(DocumentModel):
    my_loc = GeoField()


class TestKeywordQuery(unittest.TestCase):
    def test_basic_keywords(self):
        query = Query(FakeDocument)
        query.add_keywords("foo bar")

        self.assertEqual(
            u"foo bar",
            unicode(query))


class TestQuery(unittest.TestCase):
    def test_basic_keywords(self):
        query = Query(FakeDocument)
        query.add_q(Q(foo__gt=42))

        self.assertEqual(
            u"(foo > 42)",
            unicode(query))

    def test_add_q_or(self):
        """Test that two Q objects can be added to a query without needing to wrap them in
        another Q object
        """
        query = Query(FakeDocument)

        q_1 = Q(foo=42)
        q_2 = Q(foo=128)

        query.add_q(q_1)
        query.add_q(q_2, conn=Q.OR)

        self.assertEqual(
            u'((foo:"42") OR (foo:"128"))',
            unicode(query))

class TestGeoQuery(unittest.TestCase):

    def test_geosearch(self):
        query = Query(FakeGeoDocument)
        query.add_q(Q(my_loc__geo=GeoQueryArguments(3.14, 6.28, 20)))
        self.assertEqual(
            u"(distance(my_loc, geopoint(3.140000, 6.280000)) < 20)",
            unicode(query))

    def test_geosearch_lt(self):
        query = Query(FakeGeoDocument)
        query.add_q(Q(my_loc__geo_lt=GeoQueryArguments(3.14, 6.28, 20)))
        self.assertEqual(
            u"(distance(my_loc, geopoint(3.140000, 6.280000)) < 20)",
            unicode(query))

    def test_geosearch_lte(self):
        query = Query(FakeGeoDocument)
        query.add_q(Q(my_loc__geo_lte=GeoQueryArguments(3.14, 6.28, 20)))
        self.assertEqual(
            u"(distance(my_loc, geopoint(3.140000, 6.280000)) <= 20)",
            unicode(query))

    def test_geosearch_gt(self):
        query = Query(FakeGeoDocument)
        query.add_q(Q(my_loc__geo_gt=GeoQueryArguments(3.14, 6.28, 20)))
        self.assertEqual(
            u"(distance(my_loc, geopoint(3.140000, 6.280000)) > 20)",
            unicode(query))

    def test_geosearch_gte(self):
        query = Query(FakeGeoDocument)
        query.add_q(Q(my_loc__geo_gte=GeoQueryArguments(3.14, 6.28, 20)))
        self.assertEqual(
            u"(distance(my_loc, geopoint(3.140000, 6.280000)) >= 20)",
            unicode(query))


class TestDateQuery(unittest.TestCase):
    def test_before(self):
        query = Query(FakeDocument)

        today = datetime.date.today()
        query.add_q(Q(bar__lt=today))

        self.assertEqual(
            u"(bar < {0})".format(today.isoformat()),
            unicode(query))

    def test_after(self):
        query = Query(FakeDocument)

        today = datetime.date.today()
        query.add_q(Q(bar__gt=today))

        self.assertEqual(
            u"(bar > {0} AND NOT bar:{1})".format(today.isoformat(), DateField().none_value()),
            unicode(query))
