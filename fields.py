import datetime

# TODO: verify this
MAX_SEARCH_API_INT = 18446744073709551616L


class NOT_SET(object):
    pass


class FieldError(Exception):
    pass


class IndexedValue(unicode):
    pass


class Field(object):
    """Base field class. Responsible for converting the field's assigned value
    to an acceptable value for the search API.
    """
    
    def __init__(self, default=NOT_SET):
        self.default = default

    def add_to_class(self, cls, name):
        """This is a bit of a misnomer, since it's really adding details to
        this field about the class it's been assigned to, and its own
        instance name.
        """
        self.name = name
        self.cls_name = cls.__name__

    def to_search_value(self, value):
        """Convert the assigned value to a value suitable for the search API"""
        # If we don't have a value, try to set it to the default, and if
        # there's no default value set, raise an error.
        if value is None:
            if self.default is NOT_SET:
                raise FieldError('There is no default value for field %s on '
                    'class %s, yet there was no value provided'
                    % (self.name, self.cls_name))
            return self.default
        return value

    def to_python(self, value):
        """Convert the value to its python equivalent"""
        return value

    def prep_value_from_search(value):
        """Values that come directly from the result of a search may need
        pre-processing before being able to be put through either `to_python`
        or `to_search_value` methods.
        """
        return value


class TextField(Field):
    """A field for a long string of text. Accepts an optional `indexer`
    parameter for splitting the string with before it's passed to the
    search API.
    """

    def __init__(self, indexer=lambda s: s, default=''):
        self.indexer = indexer
        super(TextField, self).__init__(default=default)

    def to_search_value(self, value):
        value = super(TextField, self).to_search_value(value)

        if isinstance(value, IndexedValue):
            return value

        value = unicode(value).encode('utf-8')

        if self.indexer is None:
            return value
        return IndexedValue(self.indexer(value))

    def to_python(self, value):
        return unicode(value).encode('utf-8')

    def prep_value_from_search(self, value):
        """If this field is indexed (i.e. it has an assigned indexer) we need
        to convert the value to an `IndexedValue` so that we don't re-index it
        when calling `to_search_value`.
        """
        if self.indexer is None:
            return value
        return IndexedValue(value)


class IntegerField(Field):
    """A field representing an integer value"""
    
    def __init__(self, minimum=None, maximum=None, **kwargs):
        # Allow minimum and maximum constraints to be applied to the field
        # value
        self.minimum = minimum or -MAX_SEARCH_API_INT
        self.maximum = maximum or MAX_SEARCH_API_INT
        super(IntegerField, self).__init__(**kwargs)

    def to_search_value(self, value):
        value = super(IntegerField, self).to_search_value(value)
        value = int(value)

        if value < self.minimum or value > self.maximum:
            raise FieldError('Value %s is outwith %s-%s'
                % (value, self.minimum, self.maximum))

        return value

    def to_python(self, value):
        return int(value)


class FloatField(Field):
    """A field representing a floating point value"""

    def to_search_value(self, value):
        value = super(FloatField, self).to_search_value(value)
        return float(value)

    def to_python(self, value):
        return float(value)


class DateField(Field):
    """A field representing a date object"""

    FORMAT = '%Y-%m-%d'

    def __init__(self, auto_now_add=False, auto_now=False, **kwargs):
        assert not all(auto_now_add, auto_now),\
            "Can't set both `auto_now_add` and `auto_now` kwargs to True"
        self.auto_now_add = auto_now_add
        self.auto_now = auto_now
        super(IntegerField, self).__init__(**kwargs)

    def to_search_value(self, value):
        value = super(DateField, self).to_search_value(value)
        if value is None:
            return value
        if isinstance(value, datetime.date):
            return value.strftime(FORMAT)
        if isinstance(value, datetime.datetime):
            return value.date().strftime(FORMAT)
        return value

    def to_python(self, value):
        if not value:
            return value
        return datetime.date.strptime(value)

