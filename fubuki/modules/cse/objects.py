from functools import cached_property

class SearchResult:
    __slots__ = (
        '_data',
        'title',
        'title_html',
        'url',
        'snippet',
        'snippet_html',
        'image_url'
    )

    def __init__(self, result_data):
        self._data = result_data

        self.title = result_data.get('title')
        self.snippet = result_data.get('snippet')

        self.image_url = None
        if (image := result_data.get('image')):
            self.image_url = result_data.get('link')
            self.url = image.get('contextLink', self.image_url)
        else:
            self.url = result_data.get('link')

        self.title_html = result_data.get('htmlTitle')
        self.snippet_html = result_data.get('htmlSnippet')

    def __repr__(self):
        return '<{0.__class__.__name__} title={0.title!r} url={0.url!r}>'.format(self)

class GoogleResponse:
    __slots__ = ('_data', '__dict__')

    def __init__(self, response_data):
        self._data = response_data

    def __repr__(self):
        return '<{0.__class__.__name__} result_count={1!r}>'.format(self, len(self.results))

    @cached_property
    def request(self):
        return self._data['queries']['request']

    @cached_property
    def next_page(self):
        return self._data['queries']['nextPage']

    @cached_property
    def search_info(self):
        return self._data['searchInformation']

    @cached_property
    def results(self):
        _results = self._data.get('items', [])
        return [*map(SearchResult, _results)]

    def __iter__(self):
        return iter(self.results)
