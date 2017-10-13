import re
import string as string_module


QUOTES = (u"'", u'"')
ALLOWED_PUNCTUATION = (u"_", u"-", u"@", u'.')


class KeywordSearch(object):
    """A filter backend that executes a search query on an endpoint that is
    searchable. Meant to be integrated with views that extend from SearchMixin.
    """
    def __init__(self, get_param="search"):
        self.get_param = get_param

    def __call__(self):
        return self

    def filter_queryset(self, request, queryset, view):
        if getattr(view, "is_searching", lambda: False)():
            query = self.get_search_query(request)
            if query:
                return filter_search(queryset, query)
        return queryset

    def get_search_query(self, request):
        return request.GET.get(self.get_param)


def is_wrapped_in_quotes(string):
    """Check to see if the given string is quoted"""
    return string[0] in QUOTES and string[0] == string[-1]


def strip_surrounding_quotes(string):
    """Strip quotes from the ends of the given string"""
    if not is_wrapped_in_quotes(string):
        return string

    to_strip = string[0]
    return string.strip(to_strip)


def strip_special_search_characters(string):
    """Some punctuation characters break the Search API's query parsing if
    they're not escaped. Some punctuation characters break even if escaped.
    There's no documentation as to which characters should be escaped and which
    should be completely removed, so to stop _all_ errors, we remove all common
    punctuation to avoid brokenness.
    """
    for char in string_module.punctuation:
        if char not in ALLOWED_PUNCTUATION:
            string = string.replace(char, u"")
    return string


def strip_multi_value_operators(string):
    """The Search API will parse a query like `PYTHON OR` as an incomplete
    multi-value query, and raise an error as it expects a second argument
    in this query language format. To avoid this we strip the `AND` / `OR`
    operators tokens from the end of query string. This does not stop
    a valid multi value query executing as expected.
    """
    # the search API source code lists many operators in the tokenNames
    # iterable, but it feels cleaner for now to explicitly name only the ones
    # we are interested in here
    if string:
        string = re.sub(r'^(OR|AND)', '', string)
        string = re.sub(r'(OR|AND)$', '', string)
        string = string.strip()
    return string


def build_corpus_search(queryset, value):
    """Builds up a corpus search taking into account words which may contain
    punctuation causes a string to be tokenised by the search API and searches those
    terms exactly
    """
    value = strip_special_search_characters(value)

    # pull out words containing ALLOWED_PUNCTUATION and search with exact
    # this is mainly for searching for email addresses within the corpus
    terms = []
    for term in value.split(' '):
        if any(c in ALLOWED_PUNCTUATION for c in term):
            queryset = queryset.filter(corpus=term)
        else:
            terms.append(term)

    value = u' '.join(terms)

    value = strip_multi_value_operators(value)

    if value:
        # TODO: this doesn't handle users searching for an email address AND other terms
        queryset = queryset.filter(corpus__contains=value)

    return queryset


def filter_search(queryset, value):
    if not value:
        return queryset

    exact = is_wrapped_in_quotes(value)
    value = strip_surrounding_quotes(value)

    if exact:
        # whole search term is exact
        return queryset.filter(corpus=value)

    queryset = build_corpus_search(queryset, value)

    return queryset
