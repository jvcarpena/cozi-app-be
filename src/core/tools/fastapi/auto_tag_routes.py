import operator
import re
from itertools import accumulate

from fastapi import FastAPI
from fastapi.routing import APIRoute
from pygtrie import StringTrie


def auto_tag_routes(app: FastAPI):

    routes = [route for route in app.routes if isinstance(route, APIRoute)]

    fragmented_api_paths = [
        fragment for route in routes for fragment in accumulate(re.findall("/[^/]*", route.path), operator.add)
    ]

    trie = StringTrie()

    for fragment in fragmented_api_paths:

        trie[fragment] = trie.get(fragment, 0) + 1

    _ = [trie.pop(path) for path, count in trie.items() if count <= 0]

    _ = [route.tags.append(trie.longest_prefix(route.path).key) for route in routes]

    app.servers.insert(0, {"url": app.root_path})

    app.openapi()["x-tagGroups"] = [
        {
            "name": "Guest",
            "tags": trie.keys("/guest"),
        },
        {
            "name": "Manager",
            "tags": trie.keys("/manager"),
        },
    ]
