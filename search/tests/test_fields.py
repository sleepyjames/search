from datetime import date, datetime
import calendar
import unittest

from google.appengine.api.search import GeoPoint

from search import errors, fields, indexers, timezone


class Base(object):

    def new_field(self, field_class, **kwargs):
        f = field_class(**kwargs)
        f.name = 'test_field'
        f.cls_name = 'TestDocument'
        return f

    def test_to_search_value_null_no_default(self):
        f = self.new_field(self.field_class, null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_no_null_no_default(self):
        f = self.new_field(self.field_class, null=False)
        self.assertRaises(errors.FieldError, f.to_search_value, None)

    def test_to_search_value_null_default(self):
        f = self.new_field(self.field_class, default='THINGS', null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_no_null_default(self):
        f = self.new_field(self.field_class, default='THINGS', null=False)
        self.assertEquals(f.to_search_value(None), 'THINGS')

    def test_to_search_value_none(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value(None), f.none_value())


class TestBaseField(Base, unittest.TestCase):
    field_class = fields.Field

    def test_contribute_to_class(self):
        class FakeDocument(object):
            pass

        f = fields.Field()
        f.add_to_class(FakeDocument, 'test_field')
        self.assertEqual(f.name, 'test_field')
        self.assertEqual(f.cls_name, 'FakeDocument')


class TestTextField(Base, unittest.TestCase):
    field_class = fields.TextField

    def test_indexed_value(self):
        f = self.new_field(self.field_class, indexer=indexers.contains)
        value = f.to_search_value("Hello")
        self.assertEqual(
            sorted(indexers.contains("Hello")),
            sorted(value.split(" "))
        )


class TestFloatField(Base, unittest.TestCase):
    field_class = fields.FloatField

    def test_to_search_value_null_default(self):
        f = self.new_field(self.field_class, default=123.0, null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_null_default_2(self):
        f = self.new_field(self.field_class, default=123.0, null=True)
        self.assertEquals(f.to_search_value(987.0), 987.0)

    def test_to_search_value_no_null_default(self):
        f = self.new_field(self.field_class, default=123.0, null=False)
        self.assertEquals(f.to_search_value(None), 123.0)

    def test_to_search_value_no_null_default_2(self):
        f = self.new_field(self.field_class, default=123.0, null=False)
        self.assertEquals(f.to_search_value(987.0), 987.0)

    def test_to_search_value_floatstring(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value('987.0'), 987.0)

    def test_to_search_value_int(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value(987), 987.0)

    def test_max_min_limits(self):
        f = self.new_field(self.field_class, minimum=2.0, maximum=4.7)
        self.assertEquals(f.to_search_value(2.0), 2.0)
        self.assertEquals(f.to_search_value(4.7), 4.7)
        self.assertEquals(f.to_search_value(None), f.none_value())
        self.assertRaises(ValueError, f.to_search_value, 4.8)
        self.assertRaises(ValueError, f.to_search_value, 1.9)


class TestIntegerField(Base, unittest.TestCase):
    field_class = fields.IntegerField

    def test_to_search_value_null_default(self):
        f = self.new_field(self.field_class, default=456, null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_null_default_2(self):
        f = self.new_field(self.field_class, default=123.0, null=True)
        self.assertEquals(f.to_search_value(987), 987)

    def test_to_search_value_no_null_default(self):
        f = self.new_field(self.field_class, default=456, null=False)
        self.assertEquals(f.to_search_value(None), 456)

    def test_to_search_value_no_null_default_2(self):
        f = self.new_field(self.field_class, default=123.0, null=False)
        self.assertEquals(f.to_search_value(987), 987)

    def test_to_search_value_intstring(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value('987'), 987)

    def test_max_min_limits(self):
        f = self.new_field(self.field_class, minimum=2, maximum=4)
        self.assertEquals(f.to_search_value(2), 2)
        self.assertEquals(f.to_search_value(4), 4)
        self.assertEquals(f.to_search_value(None), f.none_value())
        self.assertRaises(ValueError, f.to_search_value, 5)
        self.assertRaises(ValueError, f.to_search_value, 1)


class TestBooleanField(Base, unittest.TestCase):
    field_class = fields.BooleanField

    def test_to_search_value_null_default(self):
        f = self.new_field(self.field_class, default=True, null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_null_default_2(self):
        f = self.new_field(self.field_class, default=True, null=True)
        self.assertEquals(f.to_search_value(False), 0)

    def test_to_search_value_no_null_default(self):
        f = self.new_field(self.field_class, default=True, null=False)
        self.assertEquals(f.to_search_value(None), 1)

    def test_to_search_value_no_null_default_2(self):
        f = self.new_field(self.field_class, default=False, null=False)
        self.assertEquals(f.to_search_value(None), 0)

    def test_to_search_value_no_null_default_3(self):
        f = self.new_field(self.field_class, default=True, null=False)
        self.assertEquals(f.to_search_value(False), 0)

    def test_to_search_value_true(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value(True), 1)

    def test_to_search_value_false(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value(False), 0)


class TestDateField(Base, unittest.TestCase):
    field_class = fields.DateField

    def test_to_search_value_null_default(self):
        f = self.new_field(self.field_class, default=date(2012, 8, 3), null=True)
        self.assertEquals(f.to_search_value(None), f.none_value())

    def test_to_search_value_null_default_2(self):
        f = self.new_field(self.field_class, default=date(2012, 8, 3), null=True)
        self.assertEquals(f.to_search_value(date(1989, 8, 3)), date(1989, 8, 3))

    def test_to_search_value_no_null_default(self):
        f = self.new_field(self.field_class, default=date(2012, 8, 3), null=False)
        self.assertEquals(f.to_search_value(None), date(2012, 8, 3))

    def test_to_search_value_no_null_default_2(self):
        f = self.new_field(self.field_class, default=date(2012, 8, 3), null=False)
        self.assertEquals(f.to_search_value(date(1989, 8, 3)), date(1989, 8, 3))

    def test_to_search_value_date(self):
        f = self.new_field(self.field_class)
        self.assertEquals(
            f.to_search_value(datetime(2012, 8, 3)), datetime(2012, 8, 3))

    def test_to_search_value_datetime(self):
        f = self.new_field(self.field_class)
        self.assertEquals(
            f.to_search_value(datetime(2012, 8, 3, 23, 49)),
            datetime(2012, 8, 3, 23, 49))

    def test_to_search_value_datestring(self):
        f = self.new_field(self.field_class)
        self.assertEquals(f.to_search_value('2012-08-03'), date(2012, 8, 3))

    def test_to_search_value_errors(self):
        f = self.new_field(self.field_class)
        self.assertRaises(ValueError, f.to_search_value, 'some nonsense')
        self.assertRaises(TypeError, f.to_search_value, 17)

    def test_error_using_aware_datetime(self):
        xmas = datetime(2016, 12, 25, 0, 0, tzinfo=timezone.utc)
        field = self.new_field(fields.DateField)

        with self.assertRaisesRegexp(TypeError, r'Datetime values must be offset-naive'):
            field.to_search_value(xmas)


class TestDateTimeField(Base, unittest.TestCase):
    field_class = fields.DateTimeField

    def test_to_search_value_no_null_default(self):
        xmas = datetime(2016, 12, 25, 0, 0)
        field = self.new_field(fields.DateTimeField, null=False, default=xmas)
        result = field.to_search_value(None)
        expected = calendar.timegm(xmas.timetuple())

        self.assertEqual(result, expected)

    def test_error_using_aware_datetime(self):
        xmas = datetime(2016, 12, 25, 0, 0, tzinfo=timezone.utc)
        field = self.new_field(fields.DateTimeField)

        with self.assertRaisesRegexp(TypeError, r'Datetime values must be offset-naive'):
            field.to_search_value(xmas)

    def test_error_using_too_early_datetime(self):
        timestamp = fields.MIN_SEARCH_API_INT - 1
        olden_times = datetime.utcfromtimestamp(timestamp)
        field = self.new_field(fields.DateTimeField)

        with self.assertRaisesRegexp(ValueError, r'Datetime out of range'):
            field.to_search_value(olden_times)

    def test_error_using_too_late_datetime(self):
        timestamp = fields.MAX_SEARCH_API_INT + 1
        future_times = datetime.utcfromtimestamp(timestamp)
        field = self.new_field(fields.DateTimeField)

        with self.assertRaisesRegexp(ValueError, r'Datetime out of range'):
            field.to_search_value(future_times)


class TestTZDateTimeField(Base, unittest.TestCase):
    field_class = fields.TZDateTimeField

    def test_to_search_value_no_null_default(self):
        xmas = datetime(2016, 12, 25, 0, 0, tzinfo=timezone.utc)
        field = self.new_field(fields.DateTimeField, null=False, default=xmas)
        result = field.to_search_value(None)
        expected = calendar.timegm(xmas.timetuple())

        self.assertEqual(result, expected)

    def test_error_using_naive_datetime(self):
        xmas = datetime(2016, 12, 25, 0, 0, tzinfo=None)
        field = self.new_field(fields.TZDateTimeField)

        with self.assertRaisesRegexp(TypeError, r'Datetime values must be offset-aware'):
            field.to_search_value(xmas)


class TestGeoField(Base, unittest.TestCase):
    field_class = fields.GeoField

    def test_to_search_value_no_null_default(self):
        self.assertRaises(
            AssertionError,
            self.new_field,
            self.field_class,
            default=GeoPoint(latitude=3.14, longitude=3.14),
            null=False)

    def test_to_search_value_null_default(self):
        self.assertRaises(
            AssertionError,
            self.new_field,
            self.field_class,
            default='THINGS',
            null=True)

    def test_to_search_value_no_null_no_default(self):
        f = self.new_field(self.field_class, null=False)
        self.assertRaises(TypeError, f.to_search_value, None)

    def test_to_search_value_null_no_default(self):
        self.assertRaises(
            AssertionError,
            self.new_field,
            self.field_class,
            default=None,
            null=True)

    def test_to_search_value_gp(self):
        f = self.new_field(self.field_class)
        gp = GeoPoint(latitude=4.2, longitude=4.2)
        self.assertEquals(f.to_search_value(gp), gp)

    def test_to_search_value_none(self):
        f = self.new_field(self.field_class)
        self.assertRaises(TypeError, f.to_search_value, None)

    def test_to_search_value_errors(self):
        f = self.new_field(self.field_class)

        # TODO: maybe support these at some point?
        self.assertRaises(TypeError, f.to_search_value, '3.14,3.14')
        self.assertRaises(TypeError, f.to_search_value, 3.14)
        self.assertRaises(TypeError, f.to_search_value, (3.14, 3.14,))
