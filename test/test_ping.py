
import asyncio
from collections import namedtuple
from typing import Any, NamedTuple


import pytest

from comitup_watch.pingmon import ping_host, ping

@pytest.mark.asyncio
async def test_ping_asyncio_null():
    pass

class PingGen(NamedTuple):
    queue: Any
    clist: Any

@pytest.fixture
def pingen():

    CListEntry = namedtuple("CListEntry", ["host"])

    clist_mock = [
        CListEntry("foo"),
        CListEntry("bar"),
    ]

    queue = asyncio.Queue()

    return PingGen(queue, clist_mock)


@pytest.mark.asyncio
async def test_ping_generic_gen():
    await asyncio.sleep(0.1)

    async def gen():
        yield 1
        yield 2

    async for x in gen():
        pass

    assert [x async for x in gen()] == [1, 2]


@pytest.mark.asyncio
async def test_ping_pinggen_base(pingen):
    results = []
    async for host in ping_host(0.02, pingen.queue, pingen.clist):
        results.append(host)

        if len(results) == 4:
            break

    assert results == ["foo", "bar", "foo", "bar"]


@pytest.mark.asyncio
async def test_ping_pinggen_base(pingen):
    await pingen.queue.put("baz")
    results = []
    async for host in ping_host(0, pingen.queue, pingen.clist):
        results.append(host)

        if len(results) == 5:
            break

    assert results == ["baz", "foo", "bar", "foo", "bar"]

@pytest.mark.asyncio
async def test_ping_pinggen_timeout(pingen):


    ph = ping_host(10, pingen.queue, pingen.clist)

    # cycle through the hosts, to get to a timeout situation
    assert await ph.__anext__() == "foo"
    assert await ph.__anext__() == "bar"

    # add an immediate task
    await pingen.queue.put("baz")

    # this should return right away
    assert await ph.__anext__() == "baz"

@pytest.mark.parametrize("case", [("127.0.0.1", True), ("10.1.2.2", False)])
# @pytest.mark.parametrize("case", [("127.0.0.1", True)])
@pytest.mark.asyncio
async def test_ping(case):
    assert await ping(case[0]) == case[1]
