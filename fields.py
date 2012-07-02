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

    def __init__(self, default=NOT_SET):
        self.default = default

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
            if self.default is NOT_SET:
                raise FieldError('There is no default value for field %s on '
                    'class %s, yet there was no value provided'
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

