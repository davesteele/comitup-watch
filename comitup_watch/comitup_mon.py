import asyncio
from bisect import bisect_left
from functools import total_ordering
from typing import Optional

from .avahi_watch import AvahiMessage
from .devicemon import DeviceMonMsg


@total_ordering
class ComitupHost:
    avahi_attrs = {
        "avahi_key": "key",
        "domain": "host",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
    }

    nm_attrs = {
        "ssid": "ssid",
    }

    def __init__(self, hostname) -> None:
        self.host: str = hostname

        self.all_attrs = self.avahi_attrs.copy()
        self.all_attrs.update(self.nm_attrs)

        for key in self.all_attrs:
            setattr(self, key, None)

    def add_avahi(self, msg: AvahiMessage) -> None:
        for key in self.avahi_attrs:
            setattr(self, key, getattr(msg, self.avahi_attrs[key]))

    def rm_avahi(self) -> None:
        for key in self.avahi_attrs:
            setattr(self, key, None)

    def add_nm(self, msg: DeviceMonMsg) -> None:
        for key in self.nm_attrs:
            setattr(self, key, getattr(msg, self.nm_attrs[key]))

    def rm_nm(self) -> None:
        for key in self.nm_attrs:
            setattr(self, key, None)

    def has_data(self) -> bool:
        return any([getattr(self, x) for x in self.all_attrs])

    def __eq__(self, other):
        return self.host == other.host

    def __lt__(self, other):
        return self.host < other.host


class ComitupList:
    def __init__(self):
        self.list = []

    def __len__(self) -> None:
        return len(self.list)

    def get_host_by_attr(self, attr: str, val: str) -> ComitupHost:
        try:
            return [x for x in self.list if getattr(x, attr) == val][0]
        except IndexError:
            return None

    def get_host(self, hostname: str) -> ComitupHost:
        return self.get_host_by_attr("host", hostname)

    def add_host(self, host: ComitupHost) -> int:
        if self.get_host(host.host):
            raise Exception("Attempted to add duplicate host")

        index: int = bisect_left(self.list, host)
        self.list.insert(index, host)

        return index

    def _index(self, hostname: str) -> int:
        index = [
            index
            for index, host in enumerate(self.list)
            if host.host == hostname
        ][0]
        return index

    def rm_host(self, hostname: str) -> None:
        index = self._index(hostname)
        del self.list[index]

    def __getitem__(self, index):
        return self.list.__getitem__(index)


class ComitupMon:
    def __init__(self):
        self.q = asyncio.Queue()

    def event_queue(self):
        return self.q

    async def run(self):
        while True:
            await asyncio.sleep(1)
