#!/usr/bin/env python3

import time
import sys
import re
from collections import defaultdict
from urllib.parse import quote, unquote
import aiohttp
import asyncio

USER_AGENT = (
    "WikiPhilosophyBot/1.0 "
    "(contact: sultanova.amaliya@list.ru)"
)


async def get_content(session, name):
    url = f'https://ru.wikipedia.org/wiki/{quote(name)}'
    try:
        async with session.get(url, allow_redirects=True) as response:
            response.raise_for_status()
            return await response.text()
    except Exception:
        return None


def extract_links(page):
    links = set()
    pattern = r'href=["\']([^"\']+)["\']'
    matches = re.findall(pattern, page, flags=re.IGNORECASE)

    for href in matches:
        name = None

        if '/wiki/' in href:
            name = href.split('/wiki/')[-1]
        elif href.startswith('./'):
            name = href[2:]

        if name is None or ":" in name:
            continue

        clean_name = name.split('#')[0].split('?')[0]

        if clean_name:
            links.add(unquote(clean_name))

    return links


async def build_node(session, frontier):
    pairs = []
    tasks = []

    for name in frontier:
        tasks.append(get_content(session, name))

    pages = await asyncio.gather(*tasks)

    for name, page in zip(frontier, pages):
        if page is None:
            continue

        for link in extract_links(page):
            pairs.append((name, link))

    return pairs


async def build_graph(session, start, finish):
    graph = defaultdict(set)
    visited = set()
    frontier = [start]

    cf_finish = finish.casefold()
    while cf_finish not in (visited | set(frontier)):
        if not frontier:
            return graph

        new_front = []
        results = await build_node(session, frontier)

        for name, link in results:
            visited.add(name.casefold())

            graph[name].add(link)
            if link.casefold() not in visited:
                new_front.append(link)

            if link.casefold() == cf_finish:
                return graph

        frontier = list(set(new_front))

    return graph


def _get_track(start, finish, backtrack):
    track = [finish]
    pointer = finish

    while pointer != start:
        pointer = backtrack.get(pointer, start)
        track.append(pointer)

    return track[::-1]


def find_chain(graph, start, finish):
    visited = set()
    backtrack = {}
    queue = [start]

    cf_finish = finish.casefold()

    while queue:
        top = queue.pop(0)

        for item in graph[top]:
            if item in visited:
                continue

            visited.add(item)
            backtrack[item] = top
            queue.append(item)

            if item.casefold() == cf_finish:
                return _get_track(start, item, backtrack)


async def main():
    if len(sys.argv) < 2:
        sys.exit("Start word is not specified")

    params = (sys.argv[1], 'Философия')
    headers = {"User-Agent": USER_AGENT}

    start = time.time()
    async with aiohttp.ClientSession(headers=headers) as session:
        graph = await build_graph(session, *params)

    chain = find_chain(graph, *params)
    time_len = time.time() - start

    if chain:
        print('\n'.join(chain))
        print(f"время работы: {time_len}")
    else:
        sys.exit(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError:
        pass