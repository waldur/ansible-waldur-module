#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
import uuid
from waldur_api_client.client import AuthenticatedClient
from waldur_api_client.api.projects import projects_list, projects_retrieve
from waldur_api_client.api.openstack_instances import (
    openstack_instances_list,
    openstack_instances_retrieve,
)


def _get_base_spec():
    return dict(
        access_token=dict(required=True, type="str", no_log=True),
        api_url=dict(required=True, type="str"),
        wait=dict(default=True, type="bool"),
        timeout=dict(default=600, type="int"),
        interval=dict(default=20, type="int"),
    )


def get_argument_spec(**kwargs):
    spec = _get_base_spec()
    spec.update(kwargs)
    return spec


def waldur_resource_argument_spec(**kwargs):
    spec = _get_base_spec()
    spec.update(
        dict(
            name=dict(required=True, type="str"),
            description=dict(type="str", default=""),
            state=dict(default="present", choices=["absent", "present"]),
            tags=dict(type="list", default=None),
        )
    )
    spec.update(kwargs)
    return spec


def is_uuid_like(val):
    """
    Check if value looks like a valid UUID.
    """
    if isinstance(val, uuid.UUID):
        return True
    try:
        uuid.UUID(val)
    except (TypeError, ValueError, AttributeError):
        return False
    else:
        return True


def get_project(client: AuthenticatedClient, project: str):
    if is_uuid_like(project):
        project = projects_retrieve.sync(client=client, uuid=project)
        return project
    projects = projects_list.sync(client=client, name_exact=project)
    if not projects:
        raise ValueError(f"Project '{project}' not found")
    if len(projects) > 1:
        raise ValueError(f"Multiple projects found with name '{project}'")
    return projects[0]


def get_client(module):
    return AuthenticatedClient(
        base_url=module.params["api_url"],
        token=module.params["access_token"],
        prefix="Token",
        raise_on_unexpected_status=True,
    )


def get_os_instance(client, instance_name, project_name=None):
    if is_uuid_like(instance_name):
        instance = openstack_instances_retrieve.sync(client=client, uuid=instance_name)
        if not instance:
            raise ValueError(f"Instance with name '{instance_name}' not found")
        return instance
    if project_name:
        kwargs = {"project_name": project_name}
    else:
        kwargs = {}
    instances = openstack_instances_list.sync(
        client=client, name=instance_name, **kwargs
    )
    if not instances:
        raise ValueError(f"Instance with name '{instance_name}' not found")
    return instances[0]
