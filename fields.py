from datetime import date, datetime

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
    converted back to it's python value. There's an extra step before setting
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
    """

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

    def prep_value_for_filter(self, value):
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
            return IndexedValue(self.indexer(value))

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

    def prep_value_for_filter(self, value):
        # We don't want to index the given text value when filtering with it
        # so pretend it's already been indexed by wrapping it in IndexedValue.
        return self.to_search_value(IndexedValue(value))


class HtmlField(TextField):
    """A field for a string of HTML. This inherits directly form TextField as
    there is no need to treat HTML differently from text, except to tell the
    Search API it's HTML."""
    pass


class FloatField(Field):
    """A field representing a floating point value"""

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

    def prep_value_for_filter(self, value):
        return str(self.to_search_value(value))


class IntegerField(Field):
    """A field representing an integer value"""

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

    def prep_value_for_filter(self, value):
        return str(self.to_search_value(value))


class BooleanField(Field):
    """A field representing a True/False value"""

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

    def prep_value_for_filter(self, value):
        return self.to_search_value(value)

    def prep_value_from_search(self, value):
        return bool(int(value))


class DateField(Field):
    """A field representing a date(time) object"""

    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

    def none_value(self):
        return date.max

    def to_search_value(self, value):
        value = super(DateField, self).to_search_value(value)
        if value is None:
            return self.none_value()
        if isinstance(value, (date, datetime)):
            return value
        if isinstance(value, basestring):
            return datetime.strptime(value, self.DATETIME_FORMAT).date()
        raise TypeError(value)

    def to_python(self, value):
        if value == self.none_value():
            return None
        if isinstance(value, (date, datetime)):
            return value

    def prep_value_for_filter(self, value):
        # The filter comparison value for a DateField should be a string of
        # the form 'YYYY-MM-DD'
        value = super(DateField, self).prep_value_for_filter(value)
        if value is None:
            return self.none_value()
        if isinstance(value, date):
            return value.strftime(self.DATE_FORMAT)
        if isinstance(value, datetime):
            return value.date().strftime(self.DATE_FORMAT)
        raise TypeError(value)
