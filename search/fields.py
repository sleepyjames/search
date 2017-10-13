from datetime import date, datetime

from google.appengine.api import search as search_api

from . import timezone
from .errors import FieldError


MAX_SEARCH_API_INT_64 = 18446744073709551616L

MAX_SEARCH_API_INT = 2147483647 # 2**31 - 1
MIN_SEARCH_API_INT = -MAX_SEARCH_API_INT

MAX_SEARCH_API_FLOAT = float(MAX_SEARCH_API_INT)
MIN_SEARCH_API_FLOAT = -MAX_SEARCH_API_FLOAT


class NOT_SET(object):
    pass


class IndexedValue(unicode):
    pass


class Field(object):
    """Base field class. Responsible for converting the field's assigned value
    to an acceptable value for the search API and back to Python again.

    There is some magic that happens upon setting/getting values on/from
    properties that subclass `Field`. When setting a value, it is (validated)
    and then converted to the search API value. When it's accessed, it's then
    converted back to its python value. There's an extra step before setting
    field values when instantiating document objects with search results, where
    `field.prep_value_from_search` is called before setting the attribute. The
    following information is offered as clarity on the process.

    A round trip for setting an attirbute is shown below:

    >>> obj.field = value
    >>> obj.__setattr__('field', value)
    >>> new_value = obj._meta.fields['field'].to_search_value(value)
    >>> obj.field = new_value

    If the document is being instantiated from search results, the ql.Query
    adds an extra step, allowing you to prep the returned value before calling
    `f.to_search_value` on it:

    >>> i.search('bla')
    >>> ...
    >>> # in query.SearchQuery._run
    >>> for d in results:
    ...     for f in d.fields:
    ...         new_value = d._meta.fields[f.name].prep_value_from_search(f.value)
    ...         # setattr() then puts the new_value through the journey above
    ...         setattr(d, f.name, new_value)

    Upon getting the field from the document object, the following process is
    invoked:

    >>> obj.field
    >>> obj.__getattribute__('field')
    >>> old_value = object.__getattribute__('field')
    >>> obj._meta.fields['field'].to_python(old_value)
    'some value'

    Each Field sub-class must declare what class it uses from the search API by
    setting the Field.search_api_field attribute.
    """
    search_api_field = None

    def __init__(self, default=NOT_SET, null=True):
        self.default = default
        self.null = null

    def none_value(self):
        return None

    def add_to_class(self, cls, name):
        """Allows this field object to keep track of details about its
        declaration on the owning document class.
        """
        self.name = name
        self.cls_name = cls.__name__

    def to_search_value(self, value):
        """Convert the value to a value suitable for the search API"""
        # If we don't have a value, try to set it to the default, and if
        # there's no default value set, raise an error.
        if value is None:
            if self.null:
                return self.none_value()
            if self.default is NOT_SET:
                raise FieldError('There is no default value for non-nullable '
                    'field %s on class %s, yet there was no value provided'
                    % (self.name, self.cls_name))
            return self.default
        return value

    def to_python(self, value):
        """Convert the value to its python equivalent"""
        return value

    def prep_value_from_search(self, value):
        """Values that come directly from the result of a search may need
        pre-processing before being able to be put through either `to_python`
        or `to_search_value` methods.
        """
        return value

    def prep_value_for_filter(self, value, **kwargs):
        """Different from `to_search_value`, this converts the value to an
        appropriate value for filtering it by. This is proabably only useful
        for DateFields, where the filter value in the query is different to
        the value actually given to the search API.
        """
        return value


class TextField(Field):
    """A field for a string of text. Accepts an optional `indexer` parameter
    which is a function that splits the string into tokens before it's passed
    to the search API.
    """
    search_api_field = search_api.TextField

    def __init__(self, indexer=None, **kwargs):
        self.indexer = indexer
        super(TextField, self).__init__(**kwargs)

    def none_value(self):
        return u'___NONE___'

    def to_search_value(self, value):
        value = super(TextField, self).to_search_value(value)

        if value is None:
            return self.none_value()

        # Don't want to re-index indexed values
        if isinstance(value, IndexedValue):
            return value

        if self.indexer is not None:
            return IndexedValue(u" ".join(self.indexer(value)))

        return value

    def to_python(self, value):
        if value in (None, 'None', self.none_value()):
            return None
        # For now, whatever we get back is fine
        return value

    def prep_value_from_search(self, value):
        """If this field is indexed (i.e. it has an assigned indexer) we need
        to convert the value to an `IndexedValue` so that we don't re-index it
        when calling `to_search_value`.
        """
        if self.indexer is None:
            return value
        return IndexedValue(value)

    def prep_value_for_filter(self, value, **kwargs):
        # We don't want to index the given text value when filtering with it
        # so pretend it's already been indexed by wrapping it in IndexedValue.
        return self.to_search_value(IndexedValue(value))


class HtmlField(TextField):
    """A field for a string of HTML. This inherits directly form TextField as
    there is no need to treat HTML differently from text, except to tell the
    Search API it's HTML."""
    search_api_field = search_api.HtmlField


class AtomField(TextField):
    """A field for storing a non-tokenised string
    """
    search_api_field = search_api.AtomField


class FloatField(Field):
    """A field representing a floating point value"""
    search_api_field = search_api.NumberField

    def __init__(self, minimum=None, maximum=None, **kwargs):
        """If minimum and maximum are given, any value assigned to this field
        will raise a ValueError if not in the defined range.
        """
        # According to the docs, the maximum numeric value is (1**31)-1, so
        # I assume that goes for floats too
        self.minimum = minimum or MIN_SEARCH_API_FLOAT
        self.maximum = maximum or MAX_SEARCH_API_FLOAT
        super(FloatField, self).__init__(**kwargs)

    def none_value(self):
        return MIN_SEARCH_API_FLOAT

    def to_search_value(self, value):
        value = super(FloatField, self).to_search_value(value)

        if value is None or value == self.none_value():
            return self.none_value()

        value = float(value)

        if value < self.minimum or value > self.maximum:
            raise ValueError('Value %s is outwith %s-%s'
                % (value, self.minimum, self.maximum))

        return value

    def to_python(self, value):
        if value == self.none_value():
            return None
        return float(value)

    def prep_value_for_filter(self, value, **kwargs):
        return str(self.to_search_value(value))


class IntegerField(Field):
    """A field representing an integer value"""
    search_api_field = search_api.NumberField

    def __init__(self, minimum=None, maximum=None, **kwargs):
        """If minimum and maximum are given, any value assigned to this field
        will raise a ValueError if not in the defined range.
        """
        # According to the docs, the maximum numeric value is (1**31)-1, so
        # I assume that goes for floats too
        self.minimum = minimum or MIN_SEARCH_API_INT
        self.maximum = maximum or MAX_SEARCH_API_INT
        super(IntegerField, self).__init__(**kwargs)

    def none_value(self):
        return MIN_SEARCH_API_INT

    def to_search_value(self, value):
        value = super(IntegerField, self).to_search_value(value)

        if value is None or value == self.none_value():
            return self.none_value()

        value = int(value)

        if value < self.minimum or value > self.maximum:
            raise ValueError('Value %s is outwith %s-%s'
                % (value, self.minimum, self.maximum))

        return value

    def to_python(self, value):
        if value == self.none_value():
            return None
        return int(value)

    def prep_value_for_filter(self, value, **kwargs):
        return str(self.to_search_value(value))


class BooleanField(Field):
    """A field representing a True/False value"""
    search_api_field = search_api.NumberField

    def none_value(self):
        return MIN_SEARCH_API_INT

    def to_search_value(self, value):
        value = super(BooleanField, self).to_search_value(value)

        if value is None or value == self.none_value():
            return self.none_value()

        try:
            # This is required because 'value' might be a string
            value = int(value)
        except TypeError:
            pass

        return int(bool(value))

    def to_python(self, value):
        if value == self.none_value():
            return None
        return bool(int(value))

    def prep_value_for_filter(self, value, **kwargs):
        return self.to_search_value(value)

    def prep_value_from_search(self, value):
        return bool(int(value))


class DateField(Field):
    """A field representing a date(time) object

    This field is only indexed by date. The time portion is ignored.
    See `DateTimeField` and `TZDateTimeField` for an implementation that will
    support a more precise comparator.
    """

    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

    search_api_field = search_api.DateField

    def none_value(self):
        return date.max

    def to_search_value(self, value):
        value = super(DateField, self).to_search_value(value)
        if value is None:
            return self.none_value()

        if isinstance(value, datetime):
            if timezone.is_tz_aware(value):
                raise TypeError('Datetime values must be offset-naive')
            return value

        if isinstance(value, date):
            return value

        if isinstance(value, basestring):
            for fmt in (self.DATETIME_FORMAT, self.DATE_FORMAT):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    pass
            raise ValueError
        raise TypeError(value)

    def to_python(self, value):
        if (value == self.none_value() or
                (isinstance(value, datetime) and
                    value.date() == self.none_value())):
            return None
        if isinstance(value, (date, datetime)):
            return value

    def prep_value_for_filter(self, value, filter_expr):
        # The filter comparison value for a DateField should be a string of
        # the form 'YYYY-MM-DD'
        value = super(DateField, self).prep_value_for_filter(value)
        if value is None:
            return self.none_value()

        filter_value = None
        if isinstance(value, date):
            filter_value = value.strftime(self.DATE_FORMAT)
        elif isinstance(value, datetime):
            filter_value = value.date().strftime(self.DATE_FORMAT)
        else:
            raise TypeError(value)

        if filter_expr.op.startswith("gt"):
            filter_value += " AND NOT {0}:{1}".format(filter_expr.prop_name, self.none_value())

        return filter_value


class DateTimeField(Field):
    """Allows searching by date including the time component.

    It works by representing a Python datetime as a unix timestamp and
    storing the value in a number field. This means you can only use datetimes
    between datetime(1901, 12, 13, 20, 45, 54) and datetime(2038, 1, 19, 3, 14, 7),
    and it ignores microseconds. Using a value outside that range will raise
    a ValueError.

    It will raise a TypeError if used with offset-aware datetime instances.
    """
    search_api_field = search_api.NumberField

    def none_value(self):
        return MIN_SEARCH_API_INT

    def to_search_value(self, value):
        value = super(DateTimeField, self).to_search_value(value)

        if value is None or value == self.none_value():
            return self.none_value()

        if timezone.is_tz_aware(value):
            if value == self.default:
                # The TZ-aware sub-class can set a default with a tzinfo.
                value = value.astimezone(timezone.utc)
                value = value.replace(tzinfo=None)
            else:
                raise TypeError('Datetime values must be offset-naive')

        timestamp = timezone.datetime_to_timestamp(value)

        # You aren't allowed to have the min value, we reserve that for None.
        if not (MIN_SEARCH_API_INT < timestamp <= MAX_SEARCH_API_INT):
            raise ValueError('Datetime out of range')

        return timestamp

    def to_python(self, value):
        if value == self.none_value():
            return None
        else:
            return timezone.timestamp_to_datetime(value)

    def prep_value_for_filter(self, value, filter_expr=None):
        return self.to_search_value(value)

    def prep_value_from_search(self, value):
        return self.to_python(value)


class TZDateTimeField(DateTimeField):
    """Like DateTimeField, but raises a TypeError if used with offset-naive
    datetime instances.
    """
    def to_search_value(self, value):
        if isinstance(value, datetime):
            try:
                value = value.astimezone(timezone.utc)
            except ValueError:
                raise TypeError('Datetime values must be offset-aware')

            value = value.replace(tzinfo=None)

        return super(TZDateTimeField, self).to_search_value(value)

    def to_python(self, value):
        value = super(TZDateTimeField, self).to_python(value)

        if value:
            return value.replace(tzinfo=timezone.utc)


class GeoField(Field):
    """ A field representing a GeoPoint """
    search_api_field = search_api.GeoField

    def __init__(self, default=None, null=False):
        assert not (null or default), "GeoField must always be non-null"
        self.default = None
        self.null = False

    def to_search_value(self, value):
        value = super(GeoField, self).to_search_value(value)

        if isinstance(value, search_api.GeoPoint):
            return value

        raise TypeError(value)
