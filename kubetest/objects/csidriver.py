"""Kubetest wrapper for the Kubernetes ``CSIDriver`` API Object."""

import logging
from typing import Any, Optional

from kubernetes import client
from kubernetes.client import ApiException

from kubetest.objects import ApiObject

LOG = logging.getLogger("kubetest")


class CSIDriver(ApiObject):
    """Kubetest wrapper around a Kubernetes `CSIDriver`_ API Object.

    The actual ``kubernetes.client.V1CSIDriver`` instance that this
    wraps can be accessed via the ``obj`` instance member.

    This wrapper provides some convenient functionality around the
    API Object and provides some state management for the `V1CSIDriver`_.

    .. _CSIDriver:
        https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.32/#csidriver-v1-storage-k8s-io
    """

    obj_type = client.V1CSIDriver

    api_clients = {
        "preferred": client.StorageV1Api,
        "v1": client.StorageV1Api,
    }

    def create(self, namespace: str = None) -> None:
        # TODO ?
        pass

    def delete(self, options: client.V1DeleteOptions = None) -> Optional[Any]:
        if options is None:
            options = client.V1DeleteOptions()

        LOG.info(f'deleting csi "{self.name}"')
        LOG.debug(f"delete options: {options}")
        LOG.debug(f"csi: {self.obj}")
        try:
            self.refresh()

            return self.api_client.delete_csi_driver(
                name=self.name,
                body=options,
            )
        except ApiException as e:
            # If we can no longer find the csi, it is already deleted.
            if e.status == 404 and e.reason == "Not Found":
                return None
            else:
                # If we get any other exception, raise it.
                LOG.error("error deleting persistent volume")
                raise e

    def refresh(self) -> None:
        """Refresh the underlying Kubernetes CSI resource."""
        self.obj = self.api_client.read_csi_driver(
            self.name,
        )

    def is_ready(self) -> bool:
        pass

    def attach_required(self) -> bool:
        return self.obj.spec.attach_required

    def fs_group_policy(self) -> str:
        return self.obj.spec.fs_group_policy

    def pod_info_on_mount(self) -> bool:
        return self.obj.spec.pod_info_on_mount

    def requires_republish(self) -> bool:
        return self.obj.spec.requires_republish

    def storage_capacity(self) -> bool:
        return self.obj.spec.storage_capacity

    def volume_lifecycle_modes(self) -> bool:
        return self.obj.spec.volume_lifecycle_modes
