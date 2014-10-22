import unittest

from search.ql import Query, Q, GeoQueryArguments
from search.fields import TextField, GeoField
from search.indexes import DocumentModel


class FakeDocument(DocumentModel):
    foo = TextField()


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
