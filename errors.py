class Error(Exception):
    pass


class FieldLookupError(Error):
    pass


class BadValueError(Error):
    pass


class DocumentClassRequiredError(Error):
    pass
