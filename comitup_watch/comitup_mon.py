import asyncio
import logging
import os
import re
from bisect import bisect_left
from datetime import datetime, timedelta
from functools import total_ordering, wraps
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import List, NamedTuple, Optional

import tabulate
# from colorama import Back, Fore, Style

from .avahi_watch import AvahiMessage
from .devicemon import DeviceMonMsg
from .pingmon import PingMessage
from .display import Display
from .table import Cell, Table

new_delta = timedelta(seconds=30)

start_time = datetime.now()


def deflog(verbose: bool = False) -> logging.Logger:
    level = logging.INFO
    if verbose:
        level = logging.DEBUG

    logdirpath = Path("~/.config/comitup-watch").expanduser()
    if not logdirpath.is_dir():
        logdirpath.mkdir(parents=True)

    log = logging.getLogger("comitup-watch")
    log.setLevel(level)
    handler = TimedRotatingFileHandler(
        str(logdirpath / "comitup-watch.log"),
        encoding="utf=8",
        when="W0",
        backupCount=8,
    )
    fmtr = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(fmtr)
    log.addHandler(handler)

    return log


def Update(kind):
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            self.update(kind)
            return fn(self, *args, **kwargs)

        return wrapper

    return decorator


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

    ping_attrs = {"ping_status": "name"}

    def __init__(self, hostname, event_q, log) -> None:
        self.host: str = hostname

        init_time = datetime.now() - 2 * new_delta
        self.update_time = {
            "ping": init_time,
            "nm": init_time,
            "avahi": init_time,
        }

        self.update_flag = True

        self.last_check = datetime.now()

        self.all_attrs = self.avahi_attrs.copy()
        self.all_attrs.update(self.nm_attrs)
        self.all_attrs.update(self.ping_attrs)

        for key in self.all_attrs:
            setattr(self, key, None)

        self.q = event_q

        self.log = log

        # for typing
        self.domain: str
        self.ipv4: str
        self.ipv6: str
        self.ping_status: Optional[bool]
        self.ssid: str

    def update(self, kind):
        self.update_time[kind] = datetime.now()
        self.update_flag = True

        class UpdateMessage(NamedTuple):
            host: str

        async def display_ping(q):
            await asyncio.sleep(new_delta.seconds + 0.1)
            await q.put(UpdateMessage(self.host))

        asyncio.create_task(display_ping(self.q))

    def is_new(self, kind):
        if self.update_time[kind] - start_time > timedelta(seconds=5):
            if datetime.now() - self.update_time[kind] < new_delta:
                return True

        return False

    def needs_update(self):

        now = datetime.now()

        for kind in ["ping", "nm", "avahi"]:
            if self.last_check < self.update_time[kind] + new_delta < now:
                self.update_flag = True

        self.last_check = now

        if self.update_flag:
            self.update_flag = False
            return True
        else:
            return False

    @Update("avahi")
    def add_avahi(self, msg: AvahiMessage) -> None:
        for key in self.avahi_attrs:
            setattr(self, key, getattr(msg, self.avahi_attrs[key]))

        self.log.info(
            "Connection info - {}: {} - {}".format(
                self.domain, self.ipv4, self.ipv6
            )
        )

    @Update("avahi")
    def rm_avahi(self) -> None:
        for key in self.avahi_attrs:
            setattr(self, key, None)

        self.update("avahi")

    @Update("nm")
    def add_nm(self, msg: DeviceMonMsg) -> None:
        for key in self.nm_attrs:
            setattr(self, key, getattr(msg, self.nm_attrs[key]))

    @Update("nm")
    def rm_nm(self) -> None:
        for key in self.nm_attrs:
            setattr(self, key, None)

    def add_ping(self, msg: PingMessage):
        if not self.ping_status:
            self.log.info("Ping success - {}".format(self.host))
            self.update("ping")

        self.ping_status = True

    def rm_ping(self):
        if self.ping_status:
            self.log.info("Ping failure - {}".format(self.host))
            self.update("ping")

        if self.ping_status is not None:
            self.ping_status = False

    def has_data(self) -> bool:
        return any([getattr(self, x) for x in self.all_attrs])

    def __eq__(self, other):
        return self.host == other.host

    def __lt__(self, other):
        return self.host < other.host

    def colorize(self, kind, text):
        output = text
        if type(output) != str:
            output = ""

        # if self.is_new(kind):
        #     output = Fore.GREEN + output + Style.RESET_ALL

        return output

    def get_display_row(self):
        if self.ping_status is None:
            pstat = None
        else:
            pstat = "  \u2714" if self.ping_status else "  \u274C"

        return [
            self.colorize("nm", self.ssid),
            self.colorize("avahi", self.domain),
            self.colorize("avahi", self.ipv4),
            self.colorize("avahi", self.ipv6),
            self.colorize("ping", pstat),
        ]

    def get_headers(self) -> List[str]:
        return ["SSID", "Domain Name", "IPv4", "IPv6", "Ping"]

    def get_cell_row(self) -> List[Cell]:
        pstat: str
        if self.ping_status is None:
            pstat = ""
        else:
            pstat = "  \u2714" if self.ping_status else "  \u274C"

        return [
            Cell(self.ssid, self.is_new("nm")),
            Cell(self.domain, self.is_new("avahi")),
            Cell(self.ipv4, self.is_new("avahi")),
            Cell(self.ipv6, self.is_new("avahi")),
            Cell(pstat, self.is_new("ping")),
        ]


class ComitupList:
    def __init__(self, event_q, log):
        self.list = []
        self.log = log
        self.q = event_q

    def __len__(self) -> int:
        return len(self.list)

    def get_host_by_attr(self, attr: str, val: str) -> Optional[ComitupHost]:
        try:
            return [x for x in self.list if getattr(x, attr) == val][0]
        except IndexError:
            return None

    def get_host(self, hostname: str) -> Optional[ComitupHost]:
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
        self.ping_q = asyncio.Queue()

        self.log = deflog()

        self.clist = ComitupList(self.q, self.log)

        self.log.info("Starting comitup-watch")

    def event_queue(self):
        return self.q

    def ping_queue(self):
        return self.ping_q

    def get_host(self, hostname):
        host = self.clist.get_host(hostname)

        if host is None:
            host = ComitupHost(hostname, self.q, self.log)
            self.clist.add_host(host)

        return host

    def proc_dev_msg(self, msg):
        host = self.get_host(msg.ssid)
        if msg.action.name == "ADDED":
            self.log.info("Added SSID = {}".format(host.host))
            host.add_nm(msg)
        else:
            self.log.info("Removed SSID = {}".format(host.host))
            host.rm_nm()
            if not host.has_data():
                self.clist.rm_host(msg.ssid)

    def proc_avahi_msg(self, msg):
        match = re.search(r"^([^\.]+)", msg.key)
        hostname = match.group(1)

        host = self.get_host(hostname)
        if msg.action.name == "ADDED":
            self.log.info("Added Network Data = {}".format(hostname))
            host.add_avahi(msg)
            try:
                self.ping_q.put_nowait(hostname)
            except asyncio.QeueueFull:
                pass

        else:
            self.log.info("Removed Network Data = {}".format(hostname))
            host.rm_avahi()
            host.ping_status = None
            if not host.has_data():
                self.clist.rm_host(hostname)

    def proc_ping_msg(self, msg):
        host = self.get_host(msg.name)

        if msg.action.name == "ADDED":
            host.add_ping(msg)
        else:
            host.rm_ping()
            if not host.has_data():
                self.clist.rm_host(msg.name)

    def test_table(self):
        # table = [x.get_display_row() for x in self.clist]

        # return table

        table = Table("SSID", "Domain Name", "IPv4", "IPv6", "Ping")

        for host in self.clist:
            table.add_row(*host.get_cell_row())

        return table




    def print_list(self):
        # # os.system("clear")

        # header = ["SSID", "Domain Name", "IPv4", "IPv6", "Ping"]

        # tabulate.PRESERVE_WHITESPACE = True
        # table_text = tabulate.tabulate(self.test_table(), header)
        # # width = max(len(x) for x in table_text.split("\n") if "--" in x)

        # #print("-" * width)
        # #print("COMITUP-WATCH".center(width))
        # #print("-" * width)

        # #print(table_text)
        # Display.instance.set_body(table_text.split("\n"))


        table = self.test_table()
        Display.instance.set_table(table)


    async def run(self):

        #print("\x1b[?25l")

        try:
            while True:
                msg = await self.q.get()

                if type(msg) == DeviceMonMsg:
                    self.proc_dev_msg(msg)
                elif type(msg) == AvahiMessage:
                    self.proc_avahi_msg(msg)
                elif type(msg) == PingMessage:
                    self.proc_ping_msg(msg)

                if any([x.needs_update() for x in self.clist]):
                    self.print_list()
        finally:
            #print("\x1b[?25h")
            pass
