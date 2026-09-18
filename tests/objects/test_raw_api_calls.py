"""Tests for the code paths that call ``ApiClient.call_api`` directly.

Unlike the generated API methods, these bypass the typed wrappers, so they are
sensitive to changes in the ``call_api`` signature and return shape between
``kubernetes`` client releases. The tests below run the real ``ApiClient`` and
only fake the HTTP transport underneath it.
"""

import io
import json
from unittest.mock import Mock

import pytest
import urllib3
from kubernetes import client

from kubetest import manager, objects

NAMESPACE = "test-ns"
TOKEN = "s3cr3t"


class FakeCluster:
    """Fake HTTP transport that answers requests by ``(method, path)``."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, method, path, body, status=200, content_type="application/json"):
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode()
        self.routes[(method, path)] = (status, body, content_type)

    def __call__(self, method, url, fields=None, headers=None, **kwargs):
        path = urllib3.util.parse_url(url).path
        self.calls.append(
            {
                "method": method,
                "path": path,
                "query": dict(fields or {}),
                "headers": headers or {},
            }
        )

        status, body, content_type = self.routes[(method, path)]
        return urllib3.HTTPResponse(
            body=io.BytesIO(body),
            status=status,
            reason="fake",
            headers={"content-type": content_type},
            preload_content=kwargs.get("preload_content", True),
        )


@pytest.fixture
def cluster(monkeypatch):
    fake = FakeCluster()
    monkeypatch.setattr(urllib3.PoolManager, "request", Mock(side_effect=fake))
    return fake


@pytest.fixture
def api_client():
    configuration = client.Configuration()
    configuration.host = "https://127.0.0.1:6443"
    configuration.api_key = {"BearerToken": TOKEN}
    configuration.api_key_prefix = {"BearerToken": "Bearer"}
    return client.ApiClient(configuration=configuration)


def owner_ref(uid, kind="ReplicaSet"):
    return {"apiVersion": "apps/v1", "kind": kind, "name": uid, "uid": uid}


def test_workload_get_pods_follows_ownership_chain(cluster, api_client):
    """Only pods owned (directly or transitively) by the workload are returned."""
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods",
        {
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": [
                {
                    "metadata": {
                        "name": "owned-pod",
                        "namespace": NAMESPACE,
                        "ownerReferences": [owner_ref("rs-owned")],
                    }
                },
                {
                    "metadata": {
                        "name": "foreign-pod",
                        "namespace": NAMESPACE,
                        "ownerReferences": [owner_ref("rs-foreign")],
                    }
                },
            ],
        },
    )
    cluster.add(
        "GET",
        f"/apis/apps/v1/namespaces/{NAMESPACE}/replicasets",
        {
            "kind": "PartialObjectMetadataList",
            "items": [
                {
                    "metadata": {
                        "uid": "rs-owned",
                        "ownerReferences": [owner_ref("deploy-uid", "Deployment")],
                    }
                },
                {
                    "metadata": {
                        "uid": "rs-foreign",
                        "ownerReferences": [owner_ref("other-uid", "Deployment")],
                    }
                },
            ],
        },
    )
    cluster.add(
        "GET",
        f"/apis/batch/v1/namespaces/{NAMESPACE}/jobs",
        {"kind": "PartialObjectMetadataList", "items": []},
    )

    deployment = objects.Deployment(
        client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name="web", namespace=NAMESPACE, uid="deploy-uid"
            ),
            spec=client.V1DeploymentSpec(
                selector=client.V1LabelSelector(match_labels={"app": "web"}),
                template=client.V1PodTemplateSpec(),
            ),
        ),
        api_client,
    )

    pods = deployment.get_pods()

    assert [p.name for p in pods] == ["owned-pod"]
    owner_requests = [c for c in cluster.calls if "/apis/" in c["path"]]
    assert len(owner_requests) == 2
    assert all(
        c["headers"]["Accept"]
        == "application/json;as=PartialObjectMetadataList;g=meta.k8s.io;v=v1"
        for c in owner_requests
    )


def new_pod(api_client):
    return objects.Pod(
        client.V1Pod(metadata=client.V1ObjectMeta(name="web-0", namespace=NAMESPACE)),
        api_client,
    )


def test_pod_http_proxy_get(cluster, api_client):
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/proxy/healthz",
        "ok",
        content_type="text/plain",
    )

    resp = new_pod(api_client).http_proxy_get("healthz")

    assert resp.status == 200
    assert resp.data == "ok"
    assert resp.headers["content-type"] == "text/plain"
    assert cluster.calls[0]["headers"]["authorization"] == f"Bearer {TOKEN}"


def test_pod_http_proxy_get_returns_error_response(cluster, api_client):
    """Non-2xx proxy responses are returned, not raised."""
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/proxy/missing",
        "not here",
        status=404,
        content_type="text/plain",
    )

    resp = new_pod(api_client).http_proxy_get("missing")

    assert resp.status == 404
    assert resp.data == "not here"


def test_pod_http_proxy_post(cluster, api_client):
    cluster.add(
        "POST",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/proxy/echo",
        '{"answer": 42}',
        status=201,
    )

    resp = new_pod(api_client).http_proxy_post("echo", data={"question": "?"})

    assert resp.status == 201
    assert resp.json() == {"answer": 42}
    assert cluster.calls[0]["headers"]["authorization"] == f"Bearer {TOKEN}"


def test_pod_http_proxy_get_json_body_keeps_string_form(cluster, api_client):
    """JSON bodies are exposed as the string form of the parsed object."""
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/proxy/info",
        '{"ready": true, "count": 2}',
    )

    resp = new_pod(api_client).http_proxy_get("info")

    assert resp.data == "{'ready': True, 'count': 2}"
    assert resp.json() == {"ready": True, "count": 2}


LOGS = "line one\nnon-ascii: \u00e9\u2713\nline three\n"


def test_container_get_logs_returns_text(cluster, api_client):
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/log",
        LOGS,
        content_type="text/plain",
    )
    container = objects.Container(client.V1Container(name="app"), new_pod(api_client))

    assert container.get_logs(tail_lines=5) == LOGS
    assert container.search_logs("line three")
    assert cluster.calls[0]["query"]["tailLines"] == 5
    assert cluster.calls[0]["query"]["container"] == "app"


def test_yield_container_logs_returns_text(cluster, api_client):
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods",
        {
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": [
                {
                    "metadata": {"name": "web-0", "namespace": NAMESPACE},
                    "spec": {"containers": [{"name": "app"}]},
                }
            ],
        },
    )
    cluster.add(
        "GET",
        f"/api/v1/namespaces/{NAMESPACE}/pods/web-0/log",
        LOGS,
        content_type="text/plain",
    )
    meta = manager.TestMeta(
        "test", "node-id", namespace_name=NAMESPACE, api_client=api_client
    )

    (output,) = meta.yield_container_logs(tail_lines=10)

    assert LOGS in output
    assert "web-0::app" in output
