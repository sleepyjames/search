from django.core import paginator as django_paginator
from django.utils import six

from rest_framework import exceptions, pagination as drf_pagination

from ..paginator import SearchPaginator


class SearchPageNumberPagination(drf_pagination.PageNumberPagination):
    """Override the DRF paginator purely in order to hook up our SearchPaginator
    in place of the DjangoPaginator.
    """
    def paginate_queryset(self, queryset, request, view=None):
        self._handle_backwards_compat(view)

        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = SearchPaginator(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)

        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except django_paginator.InvalidPage as exc:
            msg = u'Invalid page: {message}.'.format(
                message=six.text_type(exc)
            )
            raise exceptions.NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)
