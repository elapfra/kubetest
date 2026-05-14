"""Kubetest wrapper for the Kubernetes ``HTTPRoute`` Gateway API Object."""

import logging

from kubernetes import client

from .custom_objects import CustomObject

log = logging.getLogger("kubetest")


class HTTPRoute(CustomObject):
    """Kubetest wrapper around a Kubernetes HTTPRoute Gateway API object.

    HTTPRoute is part of the Kubernetes Gateway API (gateway.networking.k8s.io/v1)
    and is the successor to Ingress in clusters using the Gateway API.

    The raw dict returned by the Kubernetes API is accessible via ``obj``.
    """

    GATEWAY_API_GROUP = "gateway.networking.k8s.io"
    GATEWAY_API_VERSION = "v1"
    GATEWAY_API_PLURAL = "httproutes"

    api_clients = {
        "preferred": client.CustomObjectsApi,
        "gateway.networking.k8s.io/v1": client.CustomObjectsApi,
        "gateway.networking.k8s.io/v1beta1": client.CustomObjectsApi,
    }

    def __init__(self, api_object, api_client=None):
        super().__init__(
            api_object,
            group=self.GATEWAY_API_GROUP,
            version=self.GATEWAY_API_VERSION,
            plural=self.GATEWAY_API_PLURAL,
            api_client=api_client,
        )

    @property
    def hostnames(self) -> list:
        """All hostnames defined in the HTTPRoute spec."""
        return self.obj.get("spec", {}).get("hostnames", [])

    @property
    def hostname(self) -> str | None:
        """The first hostname defined in the HTTPRoute spec, or None."""
        hostnames = self.hostnames
        return hostnames[0] if hostnames else None
