"""Kubetest wrapper for the Kubernetes ``version`` API Object."""

from kubernetes import client

from kubetest.objects import ApiObject


class Version(ApiObject):
    """Kubetest wrapper around a Kubernetes `VersionInfo`_ API Object.

    The actual ``kubernetes.client.VersionInfo`` instance that this
    wraps can be accessed via the ``obj`` instance member.

    This wrapper provides some convenient functionality around the
    API Object and provides some state management for the `VersionInfo`_.

    .. _VersionInfo:
        https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.25/#
    """

    obj_type = client.VersionInfo

    api_clients = {
        "preferred": client.VersionApi,
        "v1": client.VersionApi,
    }

    def __init__(self):
        super().__init__(self.get_version_code())

    def create(self, namespace: str = None) -> None:
        pass

    def delete(self, options: client.V1DeleteOptions) -> client.V1Status:
        pass

    def refresh(self) -> None:
        self.obj = self.get_version_code()

    def is_ready(self) -> bool:
        pass

    def git_version(self):
        return self.obj.git_version

    def major_minor_version(self, digit_only=False):
        """
        :param digit_only:  To parse minor version such as 28+, we keep only the leading part
        :return: major, minor tuple
        """
        minor = ""
        if digit_only:
            for char in self.obj.minor:
                if char.isdigit():
                    minor += char
                else:
                    break  # Stop when a non-digit character is encountered
        else:
            minor = self.obj.minor
        return self.obj.major, minor

    def get_version_code(self):
        return self.api_client.get_code()
