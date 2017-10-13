class RegisterError(Exception):
    pass


class __Registry(dict):
    """Registry for model -> document class mappings. Raises an error if a model
    tries to be registered twice.
    """
    def __setitem__(self, model_class, meta):
        # `meta` is a tuple of the form `(index_name, document_class, rank)`
        _meta = self.setdefault(model_class, meta)
        index_name, document_class, rank = _meta

        if document_class != meta[1]:
            raise RegisterError(
                u'Cannot register {} for model {} already registered to'
                u' {}'.format(meta[1], model_class, document_class)
            )


registry = __Registry()
