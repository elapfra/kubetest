"""Custom pytest markers for kubetest."""

import os
from typing import List

import pytest
from kubernetes import client

from kubetest import manager
from kubetest.manifest import ContextRenderer, Renderer, load_file, load_path, render
from kubetest.objects import ApiObject, ClusterRoleBinding, RoleBinding

APPLYMANIFEST_INI = (
    "applymanifest(path, render=None): "
    "load a YAML manifest file from the specified path and create it on the cluster. "
    'This marker is similar to the "kubectl apply -f <path>" command. Loading a '
    "manifest via this marker will not prohibit you from loading other manifests "
    'manually. Use the "kube" fixture to get references to the created objects. The '
    "manifest loaded via this marker is registered with the internal test case "
    'metainfo and can be waited upon for creation via the "kube" fixture\'s '
    '"wait_until_created" method.'
)

APPLYMANIFESTS_INI = (
    "applymanifests(dir, files=None, render=None): "
    "load YAML manifests from the specified path and create them on the cluster. "
    "By default, all YAML files found in the specified path will be loaded and created. "
    "If a list is passed to the files parameter, only the files in the path matching "
    "a name in the files list will be loaded and created. This marker is similar to "
    'the "kubectl apply -f <dir>" command. Loading manifests via this marker will not '
    'prohibit you from loading other manifests manually. Use the "kube" fixture to get '
    "references to the created objects. Manifests loaded via this marker are registered "
    "with the internal test case metainfo and can be waited upon for creation via the "
    '"kube" fixture\'s "wait_until_created" method.'
)

RENDER_MANIFESTS_INI = (
    "render_manifests(render, context={}): "
    "set a callable for rendering manifest templates. "
    "The render argument must be a callable that accepts a template file or string"
    "value and returns a rendered YAML document that can be applied to Kubernetes."
    "The optional context argument can be used to set template variables that are made"
    "available to the template at render time."
)

CLUSTERROLEBINDING_INI = (
    "clusterrolebinding(name, subject_kind=None, subject_name=None): "
    "create and use a Kubernetes ClusterRoleBinding for the test case. The generated "
    "cluster role binding will be automatically created and removed for each marked "
    "test. The name of the role must be specified. Only existing ClusterRoles can be "
    "used. Optionally, the subject_kind (User, Group, ServiceAccount) and subject_name "
    "can be specified to set a target subject for the ClusterRoleBinding. If no "
    "subject is specified, it will default to all users in the namespace and all "
    "service accounts. If a subject is specified, both the subject kind and name must "
    "be present. The ClusterRoleBinding will always use the apiGroup "
    '"rbac.authorization.k8s.io" for both subjects and roleRefs. For more information, '
    "see: https://kubernetes.io/docs/reference/access-authn-authz/rbac/"
)

ROLEBINDING_INI = (
    "rolebinding(kind, name, subject_kind=None, subject_name=None): "
    "create and use a Kubernetes RoleBinding for the test case. The generated role "
    "binding will use the generated test-case namespace and will be automatically "
    "removed once the test completes. The role kind (Role, ClusterRole) must be "
    "specified along with the name of the role. Only existing Roles or ClusterRoles "
    "can be used. Optionally, the subject_kind (User, Group, ServiceAccount) and "
    "subject_name can be specified to set a target subject for the RoleBinding. If "
    "no subject is specified, it will default to all users in the namespace and all "
    "service accounts. If a subject is specified, both the subject kind and name "
    "must be present. The RoleBinding will always use the apiGroup "
    '"rbac.authorization.k8s.io" for both subjects and roleRefs. For more information, '
    "see: https://kubernetes.io/docs/reference/access-authn-authz/rbac/"
)


NAMESPACE_INI = (
    "namespace(create=True, name=None): "
    "finer-grained namespace configuration for the test case. By default, a new "
    "Kubernetes namespace is generated for each test case, using the test name and a "
    "timestamp to ensure uniqueness. This marker allows you to override this behavior "
    'to define your own namespace names, or to use existing namespaces. Set "create" '
    'to False to disable namespace  creation entirely. Set "name" to a string to set '
    "the name of the namespace to create/use."
)


def register(config) -> None:
    """Register kubetest markers with pytest.

    Args:
        config: The pytest config that markers will be registered to.
    """
    config.addinivalue_line("markers", APPLYMANIFEST_INI)
    config.addinivalue_line("markers", APPLYMANIFESTS_INI)
    config.addinivalue_line("markers", RENDER_MANIFESTS_INI)
    config.addinivalue_line("markers", CLUSTERROLEBINDING_INI)
    config.addinivalue_line("markers", ROLEBINDING_INI)
    config.addinivalue_line("markers", NAMESPACE_INI)


def get_manifest_renderer_for_item(item: pytest.Item) -> Renderer:
    """Return the callable for rendering a manifest template.

    Returns the renderer set via the closest
    `pytest.mark.render_manifests` marker or `kubetest.manifest.render`
    if no marker is found.

    Args:
        item: The pytest test item.

    Returns:
        A callable for rendering manifest templates into YAML documents.
    """
    mark = item.get_closest_marker("render_manifests")
    return mark.args[0] if mark else render


def apply_manifest_from_marker(item: pytest.Item, meta: manager.TestMeta) -> None:
    """Load a manifest and create the API objects for the specified file.

    This gets called for every `pytest.mark.applymanifest` marker on
    test cases.

    Once the manifest has been loaded, the API object(s) will be registered with
    the test cases' TestMeta. This allows easier control via the "kube" fixture,
    such as waiting for all objects to be created.

    Args:
        item: The pytest test item.
        meta: The metainfo object for the marked test case.
    """
    item_renderer = get_manifest_renderer_for_item(item)
    for mark in item.iter_markers(name="applymanifest"):
        path = mark.args[0]
        renderer = mark.kwargs.get("renderer", item_renderer)
        if not callable(renderer):
            raise TypeError("renderer given is not callable")

        # Normalize the path to be absolute.
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        # Load the manifest
        context = dict(
            namespace=meta.ns, test_node_id=meta.node_id, test_name=meta.name
        )
        context_renderer = ContextRenderer(renderer, context)
        objs = load_file(path, renderer=context_renderer)

        kind_to_class = {}
        # Map all direct subclasses of ApiObject
        for cls in ApiObject.__subclasses__():
            kind_to_class[cls.__name__] = cls
            # Include all subclasses of those subclasses (e.g., Workload -> Deployment, StatefulSet)
            for sub_cls in cls.__subclasses__():
                kind_to_class[sub_cls.__name__] = sub_cls

        # For each of the loaded Kubernetes resources, wrap it in the
        # equivalent kubetest wrapper. If the object does not yet have a
        # wrapper, error out. We cannot reliably create the resource
        # without our ApiObject wrapper semantics.
        wrapped = []
        for obj in objs:
            klass = kind_to_class.get(obj.kind)
            if klass:
                wrapped.append(klass(obj))
            else:
                raise ValueError(
                    f"Unable to match loaded object to an internal wrapper class: {obj}",
                )

        meta.register_objects(wrapped)


def apply_manifests_from_marker(item: pytest.Item, meta: manager.TestMeta) -> None:
    """Load manifests and create the API objects for the specified files.

    This gets called for every `pytest.mark.applymanifests` marker on test cases.

    Once a manifest has been loaded, the API objects will be registered with the
    test cases' TestMeta. This allows some easier control via the "kube" fixture,
    such as waiting for all objects to be created.

    Args:
        item: The pytest test item.
        meta: The metainfo object for the marked test case.
    """
    item_renderer = get_manifest_renderer_for_item(item)
    for mark in item.iter_markers(name="applymanifests"):
        dir_path = mark.args[0]
        files = mark.kwargs.get("files")
        renderer = mark.kwargs.get("renderer", item_renderer)

        if not callable(renderer):
            raise TypeError("renderer given is not callable")

        # We expect the path specified to either be absolute or relative
        # from the test file. If the path is relative, add the directory
        # that the test file resides in as a prefix to the dir_path.
        if not os.path.isabs(dir_path):
            dir_path = os.path.abspath(
                os.path.join(os.path.dirname(item.fspath), dir_path)
            )

        # Setup template rendering context
        context = dict(
            dir_path=dir_path,
            namespace=meta.ns,
            test_node_id=meta.node_id,
            test_name=meta.name,
        )
        context_renderer = ContextRenderer(renderer, context)

        # If there are any files specified, we will only load those files.
        # Otherwise, we'll load everything in the directory.
        if files is None:
            objs = load_path(dir_path, renderer=context_renderer)
        else:
            objs = []
            context_renderer.context["objs"] = objs
            for f in files:
                objs.extend(
                    load_file(os.path.join(dir_path, f), renderer=context_renderer)
                )

        kind_to_class = {}
        # Map all direct subclasses of ApiObject
        for cls in ApiObject.__subclasses__():
            kind_to_class[cls.__name__] = cls
            # Include all subclasses of those subclasses (e.g., Workload -> Deployment, StatefulSet)
            for sub_cls in cls.__subclasses__():
                kind_to_class[sub_cls.__name__] = sub_cls

        # For each of the loaded Kubernetes resources, we'll want to wrap it
        # in the equivalent kubetest wrapper. If the resource does not have
        # an equivalent kubetest wrapper, error out. We cannot reliably create
        # the resource without our ApiObject wrapper semantics.
        wrapped = []
        for obj in objs:
            klass = kind_to_class.get(obj.kind)
            if klass:
                wrapped.append(klass(obj))
            else:
                raise ValueError(
                    f"Unable to match loaded object to an internal wrapper class: {obj}",
                )

        meta.register_objects(wrapped)


def rolebindings_from_marker(item: pytest.Item, namespace: str) -> List[RoleBinding]:
    """Create RoleBindings for the test case if the test is marked
    with the `pytest.mark.rolebinding` marker.

    Args:
        item: The pytest test item.
        namespace: The namespace of the test case.

    Returns:
        The RoleBindings that were generated from the test case markers.
    """
    rolebindings = []
    for mark in item.iter_markers(name="rolebinding"):
        kind = mark.args[0]
        name = mark.args[1]
        subj_kind = mark.kwargs.get("subject_kind")
        subj_name = mark.kwargs.get("subject_name")

        subj = get_custom_rbac_subject(namespace, subj_kind, subj_name)
        if not subj:
            subj = get_default_rbac_subjects(namespace)

        rolebindings.append(
            RoleBinding(
                client.V1RoleBinding(
                    metadata=client.V1ObjectMeta(
                        name=f"kubetest:{item.name}",
                        namespace=namespace,
                    ),
                    role_ref=client.V1RoleRef(
                        api_group="rbac.authorization.k8s.io",
                        kind=kind,
                        name=name,
                    ),
                    subjects=subj,
                )
            )
        )

    return rolebindings


def clusterrolebindings_from_marker(
    item: pytest.Item, namespace: str
) -> List[ClusterRoleBinding]:
    """Create ClusterRoleBindings for the test case if the test case is marked
    with the `pytest.mark.clusterrolebinding` marker.

    Args:
        item: The pytest test item.
        namespace: The namespace of the test case.

    Return:
        The ClusterRoleBindings which were generated from the test case markers.
    """
    clusterrolebindings = []
    for mark in item.iter_markers(name="clusterrolebinding"):
        name = mark.args[0]
        subj_kind = mark.kwargs.get("subject_kind")
        subj_name = mark.kwargs.get("subject_name")

        subj = get_custom_rbac_subject(namespace, subj_kind, subj_name)
        if not subj:
            subj = get_default_rbac_subjects(namespace)

        clusterrolebindings.append(
            ClusterRoleBinding(
                client.V1ClusterRoleBinding(
                    metadata=client.V1ObjectMeta(
                        name=f"kubetest:{item.name}",
                    ),
                    role_ref=client.V1RoleRef(
                        api_group="rbac.authorization.k8s.io",
                        kind="ClusterRole",
                        name=name,
                    ),
                    subjects=subj,
                )
            )
        )

    return clusterrolebindings


def get_custom_rbac_subject(
    namespace: str, kind: str, name: str
) -> List[client.RbacV1Subject]:
    """Create a custom RBAC subject for the given namespace.

    Both `kind` and `name` must be specified. If one is set and
    the other is not (None), an error will be raised.

    Args:
        namespace: The namespace of the Subject.
        kind: The subject kind. This should be one of: 'User', 'Group',
            or 'ServiceAccount'.
        name: The name of the Subject.

    Returns:
        The custom RBAC subject.

    Raises:
        ValueError: One of `kind` and `name` are None.
    """
    # check that both `kind` and `name` are set.
    if (kind and not name) or (not kind and name):
        raise ValueError(
            "One of subject_kind and subject_name were specified, but both must "
            "be specified when defining a custom Subject."
        )

    # otherwise, if a custom subject is specified, create it
    if name is not None and kind is not None:
        return [
            client.RbacV1Subject(
                api_group="rbac.authorization.k8s.io",
                namespace=namespace,
                kind=kind,
                name=name,
            )
        ]
    else:
        return []


def get_default_rbac_subjects(namespace: str) -> List[client.RbacV1Subject]:
    """Get the default RBAC Subjects.

    The default subjects will allow:
      - all authenticated users
      - all unauthenticated users
      - all service accounts

    Args:
        namespace: The namespace of the Subjects.

    Returns:
        The default RBAC subjects.
    """
    return [
        # all authenticated users
        client.RbacV1Subject(
            api_group="rbac.authorization.k8s.io",
            namespace=namespace,
            name="system:authenticated",
            kind="Group",
        ),
        # all unauthenticated users
        client.RbacV1Subject(
            api_group="rbac.authorization.k8s.io",
            namespace=namespace,
            name="system:unauthenticated",
            kind="Group",
        ),
        # all service accounts
        client.RbacV1Subject(
            api_group="rbac.authorization.k8s.io",
            namespace=namespace,
            name="system:serviceaccounts",
            kind="Group",
        ),
    ]
