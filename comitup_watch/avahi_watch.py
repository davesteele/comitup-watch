# Copyright (c) 2021 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE


import asyncio
import re
from enum import Enum
from typing import List, NamedTuple, Optional

import zeroconf
from zeroconf import ServiceBrowser, Zeroconf


class AvahiAction(Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"


class AvahiMessage(NamedTuple):
    action: AvahiAction
    key: str
    name: str
    host: str
    ipv4: str
    ipv6: str


class MyListener:
    def __init__(self, zc, loop, q):
        self.zc = zc
        self.loop = loop
        self.q = q

    def remove_service(self, zeroconf, tipe, name):
        msg = AvahiMessage(
            AvahiAction.REMOVED,
            name,
            None,
            None,
            None,
            None,
        )
        asyncio.run_coroutine_threadsafe(self.q.put(msg), self.loop)

    def get_ipv4(self, addrlist: List[str], si) -> Optional[str]:
        for candidate in addrlist:
            if re.search(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", candidate):
                return candidate

        if b"ipaddr" in si.properties:
            candidate = si.properties[b"ipaddr"].decode()

            if candidate:
                return candidate

        return None

    def get_ipv6(self, addrlist: List[str], si) -> Optional[str]:
        for candidate in addrlist:
            if re.search("^[0-9a-f:]+$", candidate):
                return candidate

        if b"ip6addr" in si.properties:
            candidate = si.properties[b"ip6addr"].decode()

            if candidate:
                return candidate

        return None

    def add_service(self, zeroconf, tipe, name):
        si = self.zc.get_service_info("_comitup._tcp.local.", name)

        msg = AvahiMessage(
            AvahiAction.ADDED,
            name,
            si.get_name(),
            si.properties[b"hostname"].decode(),
            self.get_ipv4(si.parsed_addresses(), si),
            self.get_ipv6(si.parsed_addresses(), si),
        )
        asyncio.run_coroutine_threadsafe(self.q.put(msg), self.loop)

    def update_service(self, *args, **kwargs):
        pass


async def amain(event_queue):
    loop = asyncio.get_event_loop()

    avahi_q = asyncio.Queue()

    zc = Zeroconf()
    listener = MyListener(zc, loop, avahi_q)
    ServiceBrowser(zc, "_comitup._tcp.local.", listener)

    try:
        while True:
            msg = await avahi_q.get()
            await event_queue.put(msg)
    finally:
        zeroconf.close()


def main():
    asyncio.run(amain(asyncio.Queue()))


if __name__ == "__main__":
    main()
