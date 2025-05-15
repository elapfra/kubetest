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
            selector_parts = []

            # Handle matchLabels
            if self.obj.spec.selector.match_labels:
                match_labels = self.obj.spec.selector.match_labels
                selector_parts.append(selector_string(match_labels))

            # Handle matchExpressions
            match_expressions = getattr(
                self.obj.spec.selector, "match_expressions", None
            )
            if match_expressions:
                for expr in match_expressions:
                    key = expr.key
                    operator = expr.operator
                    values = expr.values or []

                    if operator == "In":
                        selector_parts.append(f"{key} in ({','.join(values)})")
                    elif operator == "NotIn":
                        selector_parts.append(f"{key} notin ({','.join(values)})")
                    elif operator == "Exists":
                        selector_parts.append(key)
                    elif operator == "DoesNotExist":
                        selector_parts.append(f"!{key}")
                    else:
                        log.warning(
                            f"Unsupported match expression operator: {operator}"
                        )

            if selector_parts:
                selector = ",".join(selector_parts)
            else:
                log.debug(f"No valid label selectors found for {self.name}")
        else:
            log.debug(f"No selector found for {self.name}")

        # Fetch all pods matching the label selector
        pod_list = client.CoreV1Api(api_client=self.raw_api_client).list_namespaced_pod(
            namespace=self.namespace, label_selector=selector
        )

        # Filter only pods owned by this Workload Kind. e.g. StatefulSet
        workload_uid = self.obj.metadata.uid
        owned_pods = [
            Pod(pod)
            for pod in pod_list.items
            if any(
                owner.kind == self.__class__.__name__ and owner.uid == workload_uid
                for owner in pod.metadata.owner_references or []
            )
        ]

        log.debug(f"Owned pods: {[p.name for p in owned_pods]}")
        return owned_pods

    def num_replicas(self):
        self.refresh()
        return self.obj.spec.replicas
