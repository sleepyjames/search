from django.core import paginator as django_paginator

from .adapters import SearchQueryAdapter


class IsSearchingMixin(object):

    def is_searching(self):
        return isinstance(self.object_list, SearchQueryAdapter)


class SearchPage(django_paginator.Page, IsSearchingMixin):
    _objects = None

    def load_objects(self, lazy=True):
        if self._objects is None:
            if self.is_searching():
                self._objects = self.object_list.as_model_objects()
            else:
                self._objects = super(SearchPage, self).__iter__()

        # force evaluation of objects in the page
        if not lazy and not isinstance(self._objects, list):
            self._objects = list(self._objects)

    def __iter__(self):
        self.load_objects()
        return iter(self._objects)


class SearchPaginator(django_paginator.Paginator, IsSearchingMixin):
    _page = None

    def _get_page(self, *args, **kwargs):
        return SearchPage(*args, **kwargs)

    def validate_number(self, number):
        """Override default handling to remove the extra search query
        """
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise django_paginator.PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise django_paginator.EmptyPage('That page number is less than 1')
        return number

    def page(self, number):
        assert not self.orphans, "SearchPaginator does not support orphans"

        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        self._page = self._get_page(self.object_list[bottom:top], number, self)

        # force evaluation at this point as we need to get the counts from the meta
        self._page.load_objects(lazy=False)

        return self._page

    def _get_count(self):
        # if we're searching then we can get the count from the
        # sliced objects list within the page
        if self.is_searching() and self._page is not None:
            return self._page.object_list.count()
        return super(SearchPaginator, self)._get_count()

    count = property(_get_count)
