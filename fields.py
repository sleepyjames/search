# TODO: verify this
MAX_SEARCH_API_INT = 18446744073709551616L


class NOT_SET(object):
    pass


class FieldError(Exception):
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
        value = unicode(value).encode('utf-8')

        if self.indexer is None:
            return value
        return self.indexer(value)


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


class FloatField(Field):
    """A field representing a floating point value"""

    def to_search_value(self, value):
        value = super(FloatField, self).to_search_value(value)
        return float(value)


