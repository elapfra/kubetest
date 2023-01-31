"""Test fixtures for kubetest unit tests."""
import json
import os
import datetime
from unittest.mock import Mock, ANY
from typing import Dict, Any

import pytest
import urllib3.request
from kubernetes import client


@pytest.fixture()
def manifest_dir():
    """Get the path to the test manifest directory."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


@pytest.fixture()
def simple_deployment():
    """Return the Kubernetes config matching the simple-deployment.yaml manifest."""
    return client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name="nginx-deployment", labels={"app": "nginx"}),
        spec=client.V1DeploymentSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "nginx"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "nginx"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="nginx",
                            image="nginx:1.7.9",
                            ports=[client.V1ContainerPort(container_port=80)],
                        )
                    ]
                ),
            ),
        ),
    )


@pytest.fixture()
def simple_statefulset():
    """Return the Kubernetes config matching the simple-statefulset.yaml manifest."""
    return client.V1StatefulSet(
        api_version="apps/v1",
        kind="StatefulSet",
        metadata=client.V1ObjectMeta(
            name="postgres-statefulset", labels={"app": "postgres"}
        ),
        spec=client.V1StatefulSetSpec(
            replicas=3,
            selector=client.V1LabelSelector(match_labels={"app": "postgres"}),
            service_name="simple-service",
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "postgres"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="postgres",
                            image="postgres:9.6",
                            ports=[client.V1ContainerPort(container_port=5432)],
                        )
                    ]
                ),
            ),
        ),
    )


@pytest.fixture()
def simple_daemonset():
    """Return the Kubernetes config matching the simple-daemonset.yaml manifest."""
    return client.V1DaemonSet(
        api_version="apps/v1",
        kind="DaemonSet",
        metadata=client.V1ObjectMeta(name="canal-daemonset", labels={"app": "canal"}),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(match_labels={"app": "canal"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "canal"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="canal",
                            image="canal:3.7.2",
                            ports=[client.V1ContainerPort(container_port=9099)],
                        )
                    ]
                ),
            ),
        ),
    )


@pytest.fixture()
def simple_service():
    """Return the Kubernetes config matching the simple-service.yaml manifest."""
    return client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name="my-service"),
        spec=client.V1ServiceSpec(
            selector={"app": "MyApp"},
            ports=[client.V1ServicePort(protocol="TCP", port=80, target_port=9376)],
        ),
    )


@pytest.fixture()
def simple_persistentvolumeclaim():
    """Return the Kubernetes config matching the simple-persistentvolumeclaim.yaml manifest."""
    return client.V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=client.V1ObjectMeta(name="my-pvc"),
        spec=client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteMany"],
            resources=client.V1ResourceRequirements(requests={"storage": "16Mi"}),
        ),
    )


@pytest.fixture()
def simple_ingress():
    """Return the Kubernetes config matching the simple-ingress.yaml manifest."""
    return client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(name="my-ingress"),
        spec=client.V1IngressSpec(
            rules=[
                client.V1IngressRule(
                    host="my-host.com",
                    http=client.V1HTTPIngressRuleValue(
                        paths=[
                            client.V1HTTPIngressPath(
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        port=client.V1ServiceBackendPort(
                                            number=80,
                                        ),
                                        name="my-service",
                                    )
                                ),
                                path="/",
                                path_type="Exact",
                            )
                        ]
                    ),
                )
            ]
        ),
    )


@pytest.fixture()
def simple_replicaset():
    """Return the Kubernetes config matching the simple-replicaset.yaml manifest."""
    return client.V1ReplicaSet(
        api_version="apps/v1",
        kind="ReplicaSet",
        metadata=client.V1ObjectMeta(
            name="frontend",
            labels={
                "app": "guestbook",
                "tier": "frontend",
            },
        ),
        spec=client.V1ReplicaSetSpec(
            replicas=3,
            selector=client.V1LabelSelector(
                match_labels={
                    "tier": "frontend",
                },
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "tier": "frontend",
                    },
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="php-redis",
                            image="gcr.io/google_samples/gb-frontend:v3",
                        ),
                    ],
                ),
            ),
        ),
    )


@pytest.fixture()
def simple_serviceaccount():
    """Return the Kubernetes config matching the simple-serviceaccount.yaml manifest."""
    return client.V1ServiceAccount(
        api_version="v1",
        kind="ServiceAccount",
        metadata=client.V1ObjectMeta(name="build-robot"),
    )


@pytest.fixture()
def simple_networkpolicy():
    """Return the Kubernetes config matching the simple-networkpolicy.yaml manifest."""
    return client.V1NetworkPolicy(
        api_version="networking.k8s.io/v1",
        kind="NetworkPolicy",
        metadata=client.V1ObjectMeta(name="default-deny"),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(),
            policy_types=["Egress", "Ingress"],
        ),
    )


@pytest.fixture()
def cluster_dir():
    """Get the path to the test manifest directory."""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/clusters")


class UnavailableHostException(BaseException):
    def __init__(self, host: str):
        self.message = f"Only 'https://127.0.0.1 and 'https://::1 clusters hosts are mocked. Host {host} not supported."


class URLOrMethodNotRecognised(BaseException):
    def __init__(self, method: str, url: str):
        self.message = f"Only '/api/v1/namespaces' POST requests are mocked. {method} requests to {url} not supported."


class MockResponse:
    def __init__(self, status: int, reason: str, data: Dict[str, Any]):
        self.status = status
        self.reason = reason
        self.data = json.dumps(data).encode() + b'\n'


@pytest.fixture
def kubernetes_requests_mock(monkeypatch):
    # mocked object, which only has the .json() method.
    def mock_urllib_request(method, url, fields=None, headers=None, **urlopen_kw):
        utc_time = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
        body = urlopen_kw.get('body')
        data = json.loads(body) if body else {}
        metadata = data.get('metadata', {})
        if method == "POST":
            if "/api/v1/namespaces" in url:
                # create namespace
                name = metadata['name']
                if url.startswith('https://127.0.0.1'):
                    uid = "00000000-0000-0000-0000-000000000000"
                elif url.startswith('https://::1'):
                    uid = "00000000-0000-0000-0000-000000000001"
                else:
                    raise UnavailableHostException
                data = {"kind": "Namespace",
                        "apiVersion": "v1",
                        "metadata":
                        {"name": name,
                          "uid": uid,
                          "resourceVersion": "121606904",
                           "creationTimestamp": utc_time,
                          "labels": {
                                 "kubernetes.io/metadata.name": name},
                          "managedFields": [{
                                "manager": "OpenAPI-Generator",
                                "operation": "Update",
                                "apiVersion": "v1",
                                 "time": utc_time,
                                 "fieldsType": "FieldsV1",
                                 "fieldsV1": {
                                     "f:metadata": {
                                         "f:labels": {
                                             ".": {}, "f:kubernetes.io/metadata.name": {}}}}}]}, "spec": {
                          "finalizers": ["kubernetes"]},
                        "status": {"phase": "Active"}}
                return MockResponse(status=201, reason="created", data=data)
        raise URLOrMethodNotRecognised
    # apply the monkeypatch for requests.get to mock_get
    mock = Mock(side_effect=mock_urllib_request)
    monkeypatch.setattr(urllib3.request.RequestMethods, "request", mock)
    yield mock


@pytest.fixture
def expected_request_kwargs():
    return lambda n: {'body': '{"metadata": {"name": "%s"}}' % n, 'preload_content': ANY,
                      'timeout': ANY,
                      'headers': {'Accept': 'application/json', 'User-Agent': ANY,
                                  'Content-Type': 'application/json'}}
