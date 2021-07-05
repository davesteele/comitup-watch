
import pytest
from collections import namedtuple

from comitup_watch.comitup_mon import ComitupHost, ComitupList
from comitup_watch.avahi_watch import AvahiAction, AvahiMessage
from comitup_watch.devicemon import DeviceMonMsg, DeviceMonAction

@pytest.fixture
def chost():
    return ComitupHost("foo")


@pytest.fixture
def clist():
    fxt = ComitupList()

    fxt.list = [
        ComitupHost("bravo"),
        ComitupHost("delta"),
    ]

    return fxt

def test_comituphost_create(chost):
    assert chost.host == "foo"

    assert chost.domain is None
    assert chost.ssid is None

    assert not chost.has_data()

def test_comituphost_compare(chost):
    host2 = ComitupHost("bar")

    assert chost == chost
    assert chost > host2

@pytest.mark.parametrize("test_rm", [True, False])
def test_comituphost_avahi_msg(chost, test_rm):
    chost.add_avahi(AvahiMessage(AvahiAction.ADDED, "key", "name", "host", "ipv4", "ipv6"))

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
    index = clist.add_host(ComitupHost(case.input))

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
