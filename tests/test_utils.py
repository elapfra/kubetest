"""Unit tests for the kubetest.utils package."""

import pytest

from kubetest import utils


@pytest.mark.parametrize(
    "name,expected",
    [
        ("", "kubetest-a80ebe94-1536849367"),
        ("TestName", "kubetest-a80ebe94-1536849367-testname"),
        ("TESTNAME", "kubetest-a80ebe94-1536849367-testname"),
        ("Test-Name", "kubetest-a80ebe94-1536849367-test-name"),
        ("Test1_FOO-BAR_2", "kubetest-a80ebe94-1536849367-test1-foo-bar-2"),
        ("123456", "kubetest-a80ebe94-1536849367-123456"),
        ("___", "kubetest-a80ebe94-1536849367"),
        (
            "test-" * 14,
            "kubetest-a80ebe94-1536849367-test-test-test-test-test-test-test",
        ),
        ("test[a]-foo", "kubetest-a80ebe94-1536849367-test-a--foo"),
    ],
)
def test_new_namespace(name, expected):
    """Test creating a new namespace for the given function name."""

    # mock the return of time.time() so we know what it will return
    utils.uuid.uuid4 = lambda: "a80ebe94-49f0-46f5-afe1-94503a3d265b"
    utils.time.time = lambda: 1536849367.0

    actual = utils.new_namespace(name)
    assert actual == expected


@pytest.mark.parametrize(
    "labels,expected",
    [
        ({}, ""),
        ({"foo": "bar"}, "foo=bar"),
        ({"foo": 2}, "foo=2"),
        ({"foo": 2.024}, "foo=2.024"),
        ({"foo": "bar", "abc": "xyz"}, "foo=bar,abc=xyz"),
        ({"foo": "bar", "abc": "xyz", "app": "synse"}, "foo=bar,abc=xyz,app=synse"),
    ],
)
def test_selector_string(labels, expected):
    """Test creating a string for a dictionary of selectors."""

    actual = utils.selector_string(labels)
    assert actual == expected
