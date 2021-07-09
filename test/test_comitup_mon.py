
import pytest
from collections import namedtuple
from typing import List
from unittest.mock import Mock

from comitup_watch.comitup_mon import ComitupHost, ComitupList, ComitupMon
from comitup_watch.avahi_watch import AvahiAction, AvahiMessage
from comitup_watch.devicemon import DeviceMonMsg, DeviceMonAction

##############################################################################
# ComitupHost
##############################################################################

@pytest.fixture
def chost():
    return ComitupHost("foo", Mock())


def test_comituphost_create(chost):
    assert chost.host == "foo"

    assert chost.domain is None
    assert chost.ssid is None

    assert not chost.has_data()

def test_comituphost_compare(chost):
    host2 = ComitupHost("bar", Mock())

    assert chost == chost
    assert chost > host2

@pytest.mark.parametrize("test_rm", [True, False])
def test_comituphost_avahi_msg(chost, test_rm):
    chost.add_avahi(AvahiMessage(AvahiAction.ADDED, "key", "host", "ipv4", "ipv6"))

    assert chost.has_data()
    assert chost.avahi_key == "key"

    if test_rm:
        chost.rm_avahi()
        assert not chost.has_data()
        assert chost.avahi_key is None

@pytest.mark.parametrize("test_rm", [True, False])
def test_comituphost_dev_msg(chost, test_rm):
    assert chost.ssid is None

    chost.add_nm(DeviceMonMsg(DeviceMonAction.ADDED, "foo"))

    assert chost.has_data()
    assert chost.ssid == "foo"

    if test_rm:
        chost.rm_nm()
        assert not chost.has_data()
        assert chost.ssid is None


##############################################################################
# ComitupList
##############################################################################

@pytest.fixture
def clist():
    fxt = ComitupList(Mock())

    fxt.list = [
        ComitupHost("bravo", Mock()),
        ComitupHost("delta", Mock()),
    ]

    return fxt

def test_comituplist_fxt(clist):
    for term in ["bravo", "delta"]:
        assert term in [x.host for x in clist.list]

    assert len(clist) == 2


def test_comituplist_get_host(clist):
    assert clist.get_host("delta").host == "delta"

def test_comituplist_get_host_by_attr(clist):
    assert clist.get_host_by_attr("host", "delta").host == "delta"

def test_comituplist_get_none(clist):
    assert clist.get_host("alpha") == None


OrderCase = namedtuple("OrderCase", ["input", "output", "index"])

@pytest.mark.parametrize(
    "case",
    [
        OrderCase("alpha", ["alpha", "bravo", "delta"], 0),
        OrderCase("charlie", ["bravo", "charlie", "delta"], 1),
        OrderCase("echo", ["bravo", "delta", "echo"], 2),
    ],
)
def test_comituplist_add_host(clist, case):
    index = clist.add_host(ComitupHost(case.input, Mock()))

    assert [x.host for x in clist.list] == case.output

    assert index == case.index

def test_comituplist_no_dups(clist):
    with pytest.raises(Exception):
        clist.add_host(ComitupHost("bravo"))


@pytest.mark.parametrize(
    "case",
    [
        OrderCase("bravo", [], 0),
        OrderCase("delta", [], 1),
    ]
)
def test_comituplist_index(clist, case):
    assert clist._index(case.input) == case.index

def test_comituplist_rm_host(clist):
    clist.rm_host("bravo")

    assert [x.host for x in clist.list] == ["delta"]

@pytest.mark.parametrize("index", range(2))
def test_comituplist_get_item(clist, index):
    assert clist[index] == clist.list[index]

##############################################################################
# ComitupMon
##############################################################################

def in_table(table: List[List[str]], teststr: str) -> bool:
    return teststr in [y for x in table for y in x]

def host_exists(com_mon, hostname):
    return hostname in [x.host for x in com_mon.clist]

def send_avahi_msg(dev_mon, action, hostname) -> None:
    msg_action = getattr(AvahiAction, action)
    msg = AvahiMessage(
        msg_action,
        hostname + "._comitup._tcp.local",
        # hostname,
        hostname + ".local",
        "ipv4-" + hostname,
        "ipv6-" + hostname,
    )
    dev_mon.proc_avahi_msg(msg)

def send_nm_msg(dev_mon, action, hostname) -> None:
    msg_action = getattr(DeviceMonAction, action)
    msg = DeviceMonMsg(msg_action, hostname)
    dev_mon.proc_dev_msg(msg)

@pytest.fixture
def com_mon(monkeypatch):
    monkeypatch.setattr("comitup_watch.comitup_mon.ComitupMon.print_list", Mock())

    fxt = ComitupMon()

    send_avahi_msg(fxt, "ADDED", "host1")
    send_nm_msg(fxt, "ADDED", "host2")

    return fxt

def test_in_table():
    testtable = [
        ["one", "two"],
        ["three", "four"],
    ]

    assert in_table(testtable, "one")
    assert in_table(testtable, "four")
    assert not in_table(testtable, "five")

def test_comitupmon_fxt(com_mon):
    assert len(com_mon.clist) == 2

    assert host_exists(com_mon, "host1")
    assert host_exists(com_mon, "host2")
    assert not host_exists(com_mon, "host3")

def test_comitupmon_add_twice(com_mon):
    send_avahi_msg(com_mon, "ADDED", "host1")
    send_nm_msg(com_mon, "ADDED", "host2")

    assert len(com_mon.clist) == 2

    assert host_exists(com_mon, "host1")
    assert host_exists(com_mon, "host2")
    assert not host_exists(com_mon, "host3")

def test_comitupmon_del_avahi(com_mon):
    send_avahi_msg(com_mon, "REMOVED", "host1")

    assert not host_exists(com_mon, "host1")
    assert len(com_mon.clist) == 1

def test_comitupmon_del_nm(com_mon):
    send_nm_msg(com_mon, "REMOVED", "host2")

    assert not host_exists(com_mon, "host2")
    assert len(com_mon.clist) == 1

def test_comitupmon_add_and_del(com_mon):
    send_nm_msg(com_mon, "ADDED", "host1")
    assert host_exists(com_mon, "host1")

    send_nm_msg(com_mon, "REMOVED", "host1")
    assert host_exists(com_mon, "host1")

    send_avahi_msg(com_mon, "REMOVED", "host1")
    assert not host_exists(com_mon, "host1")

    send_avahi_msg(com_mon, "ADDED", "host2")
    assert host_exists(com_mon, "host2")

    send_avahi_msg(com_mon, "REMOVED", "host2")
    assert host_exists(com_mon, "host2")

    send_nm_msg(com_mon, "REMOVED", "host2")
    assert not host_exists(com_mon, "host2")
