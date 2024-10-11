""" Base class for workload type objects:
daemonset, deployment, job, replicaset, statefulset
"""
import abc
import logging
from typing import List

from kubernetes import client

from kubetest.utils import selector_string

from .api_object import ApiObject
from .pod import Pod

log = logging.getLogger("kubetest")


class Workload(ApiObject):
    def __init__(self, api_object, *args, **kwargs):
        super().__init__(api_object, *args, **kwargs)
        self.klabel_key = None
        self.klabel_uid = None

    @abc.abstractmethod
    def create(self, namespace: str = None) -> None:
        pass

    @abc.abstractmethod
    def delete(self, options: client.V1DeleteOptions) -> client.V1Status:
        pass

    @abc.abstractmethod
    def refresh(self) -> None:
        pass

    @abc.abstractmethod
    def is_ready(self) -> bool:
        pass

    def get_pods(self) -> List[Pod]:
        """Get the pods for the workload.
        Returns:
            A list of pods that belong to the workload.
        """
        log.info(f'getting pods for {self.__class__.__name__} "{self.name}"')
        selector = None
        if self.klabel_key and self.klabel_uid:
            selector = selector_string({self.klabel_key: self.klabel_uid})
        elif self.obj.spec.selector:
            if self.obj.spec.selector.match_labels:
                selector = selector_string(self.obj.spec.selector.match_labels)
            elif self.obj.spec.selector.match_expressions:
                # TODO
                pass
            else:
                # TODO
                pass
        pods = client.CoreV1Api(api_client=self.raw_api_client).list_namespaced_pod(
            namespace=self.namespace, label_selector=selector
        )

        pods = [Pod(p) for p in pods.items]
        log.debug(f"pods: {[p.name for p in pods]}")
        return pods

    def num_replicas(self):
        self.refresh()
        return self.obj.spec.replicas
