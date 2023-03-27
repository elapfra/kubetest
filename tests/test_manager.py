"""Unit tests for the kubetest.manager package."""

import os
import time

from kubetest import manager


def test_manager_new_test():
    """Test creating a new TestMeta from the manager."""

    m = manager.KubetestManager()
    assert len(m.nodes) == 0

    c = m.new_test("node-id", "test-name", True, None)
    assert isinstance(c, manager.TestMeta)
    assert "kubetest-test-name-" in c.ns

    assert len(m.nodes) == 1
    assert "node-id" in m.nodes


def test_manager_new_test_with_ns_name():
    """Test creating a new TestMeta with a given namespace name
    from the manager.
    """

    m = manager.KubetestManager()
    c = m.new_test("node-id", "test-name", True, "my-test")
    assert isinstance(c, manager.TestMeta)
    assert c.ns == "my-test"
    assert c.namespace_create is True


def test_manager_new_test_without_ns():
    """Test creating a new TestMeta without namespace creation
    from the manager.
    """

    m = manager.KubetestManager()
    c = m.new_test("node-id", "test-name", False, None)
    assert isinstance(c, manager.TestMeta)
    assert c.namespace_create is False


def test_manager_get_test():
    """Test getting an existing TestMeta from the manager."""

    m = manager.KubetestManager()
    m.nodes["foobar"] = manager.TestMeta("foo", "bar", True, None)

    c = m.get_test("foobar")
    assert isinstance(c, manager.TestMeta)
    assert "foo" == c.name
    assert "bar" == c.node_id


def test_manager_get_test_none():
    """Test getting a non-existent test meta from the manager."""

    m = manager.KubetestManager()

    c = m.get_test("foobar")
    assert c is None


def test_manager_setup(cluster_dir, kubernetes_requests_mock, expected_request_kwargs):
    """Test manager for a single clusters."""

    kubeconfig = os.path.join(cluster_dir, "kube_config_cluster1.yaml")
    m1 = manager.KubetestManager()
    assert len(m1.nodes) == 0

    c = m1.new_test("node-id", "test-name", True, None, kubeconfig=kubeconfig)
    assert isinstance(c, manager.TestMeta)

    c.setup()

    kwargs = expected_request_kwargs(c.ns)
    kubernetes_requests_mock.assert_called_with(
        "POST", "https://127.0.0.1/api/v1/namespaces", **kwargs
    )

    assert "kubetest-test-name-" in c.ns

    assert len(m1.nodes) == 1
    assert "node-id" in m1.nodes

    assert c.api_client.configuration.host == "https://127.0.0.1"


def test_multiple_manager_setup(
    cluster_dir, kubernetes_requests_mock, expected_request_kwargs
):
    """Test manager for a single clusters."""

    kubeconfig1 = os.path.join(cluster_dir, "kube_config_cluster1.yaml")
    kubeconfig2 = os.path.join(cluster_dir, "kube_config_cluster2.yaml")
    m1 = manager.KubetestManager()
    m2 = manager.KubetestManager()

    assert len(m1.nodes) == 0
    assert len(m2.nodes) == 0

    c1 = m1.new_test("node-id", "test-name", True, None, kubeconfig=kubeconfig1)
    time.sleep(
        1
    )  # Guarantees second cluster namespace is generated with a different name
    c2 = m2.new_test("node-id", "test-name", True, None, kubeconfig=kubeconfig2)

    assert isinstance(c1, manager.TestMeta)
    assert isinstance(c2, manager.TestMeta)

    kwargs_c1 = expected_request_kwargs(c1.ns)
    kwargs_c2 = expected_request_kwargs(c2.ns)

    c1.setup()
    kubernetes_requests_mock.assert_called_with(
        "POST", "https://127.0.0.1/api/v1/namespaces", **kwargs_c1
    )

    c2.setup()
    kubernetes_requests_mock.assert_called_with(
        "POST", "https://::1/api/v1/namespaces", **kwargs_c2
    )

    assert "kubetest-test-name-" in c1.ns
    assert "kubetest-test-name-" in c2.ns

    assert c1.ns != c2.ns

    assert len(m1.nodes) == 1
    assert "node-id" in m1.nodes

    assert len(m2.nodes) == 1
    assert "node-id" in m2.nodes

    assert c1.api_client.configuration.host == "https://127.0.0.1"
    assert c2.api_client.configuration.host == "https://::1"
