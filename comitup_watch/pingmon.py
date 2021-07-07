import asyncio
from datetime import datetime, timedelta
from enum import Enum
from subprocess import DEVNULL
from typing import NamedTuple, Optional


class PingAction(Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"


class PingMessage(NamedTuple):
    action: PingAction
    name: str


async def ping_host(period: int, request_q: asyncio.Queue, clist):
    """Yield hosts for periodic ping, with priority to a request queue."""
    timestamp = None

    while True:
        now = datetime.now()

        if timestamp is None:
            timestamp = now

        if timestamp > now:
            delay = timestamp - now
            try:
                host = await asyncio.wait_for(
                    request_q.get(), timeout=delay.total_seconds()
                )
                yield host
            except asyncio.TimeoutError:
                pass
        else:
            timestamp = timestamp + timedelta(seconds=period)
            for host in [x.host for x in clist]:
                while not request_q.empty():
                    yield await request_q.get()

                yield host


def get_host_ip(hostname: str, clist) -> Optional[str]:
    ip = None

    host = clist.get_host(hostname)

    if host:
        ip = host.ipv4
    return ip


async def ping(ip: str) -> bool:
    cmd = "ping -c 1 " + ip
    proc = await asyncio.create_subprocess_exec(
        *cmd.split(), stdout=DEVNULL, stderr=DEVNULL
    )
    try:
        return_code = await asyncio.wait_for(proc.wait(), timeout=0.4)
    except asyncio.TimeoutError:
        return False

    return return_code == 0


async def amain(event_q, req_q, clist):

    async for hostname in ping_host(10, req_q, clist):
        ip = get_host_ip(hostname, clist)

        if ip and await ping(ip):
            msg = PingMessage(PingAction.ADDED, hostname)
        else:
            msg = PingMessage(PingAction.REMOVED, hostname)

        await event_q.put(msg)
