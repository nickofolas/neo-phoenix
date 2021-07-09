# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 nickofolas
from functools import cached_property


class SearchResult:
    __slots__ = (
        "title",
        "title_html",
        "url",
        "snippet",
        "snippet_html",
        "image_url"
    )

    def __init__(self, result_data):
        self.title = result_data.get("title")
        self.snippet = result_data.get("snippet")

        self.image_url = None
        if (image := result_data.get("image")):
            self.image_url = result_data.get("link")
            self.url = image.get("contextLink", self.image_url)
        else:
            self.url = result_data.get("link")

        self.title_html = result_data.get("htmlTitle")
        self.snippet_html = result_data.get("htmlSnippet")

    def __repr__(self):
        return "<{0.__class__.__name__} title={0.title!r} url={0.url!r}>".format(self)


class GoogleResponse:
    __slots__ = ("request", "next_page", "search_info", "results")

    def __init__(self, response_data):
        self.request = response_data["queries"]["request"]
        self.next_page = response_data["queries"].get("nextPage")
        self.search_info = response_data["searchInformation"]

        _results = response_data.get("items", [])
        self.results = [*map(SearchResult, _results)]

    def __repr__(self):
        return "<{0.__class__.__name__} result_count={1!r}>".format(self, len(self.results))

    def __iter__(self):
        return iter(self.results)
