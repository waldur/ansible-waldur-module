#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
import uuid
from ansible_waldur_module.exceptions import (
    ResourceMultipleFoundError,
    ObjectNotFoundError,
)
from waldur_api_client.client import AuthenticatedClient
from waldur_api_client.api.projects import projects_list, projects_retrieve
from waldur_api_client.api.marketplace_public_offerings import (
    marketplace_public_offerings_list,
    marketplace_public_offerings_retrieve,
)
from waldur_api_client.api.marketplace_plans import (
    marketplace_plans_list,
    marketplace_plans_retrieve,
)
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


def convert_to_mb(gb_size):
    try:
        if gb_size < 1:
            raise ValueError("Size must be at least 1 GB")
        return gb_size * 1024
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid size value: {gb_size}. Size must be a positive number in GB. Caused by {e}"
        )


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
        return projects_retrieve.sync(client=client, uuid=project)
    projects = projects_list.sync(client=client, name_exact=project)
    if not projects:
        raise ObjectNotFoundError(f"Project '{project}' not found")
    if len(projects) > 1:
        raise ResourceMultipleFoundError(
            f"Multiple projects found with name '{project}'"
        )
    return projects[0]


def get_offering(client: AuthenticatedClient, offering: str):
    if is_uuid_like(offering):
        offering_obj = marketplace_public_offerings_retrieve.sync(
            client=client, uuid=offering
        )
        return offering_obj

    offerings = marketplace_public_offerings_list.sync(
        client=client, name_exact=offering
    )
    if not offerings:
        raise ValueError(f"Offering '{offering}' not found")
    return offerings[0]


def get_plan(client: AuthenticatedClient, plan: str, offering: str = None):
    if is_uuid_like(plan):
        plan_obj = marketplace_plans_retrieve.sync(client=client, uuid=plan)
        return plan_obj
    if offering:
        offering_obj = get_offering(client, offering)
    else:
        raise ValueError("Offering is required to get a plan")
    plans = marketplace_plans_list.sync(client=client, offering_uuid=offering_obj.uuid)

    matching_plan = next((p for p in plans if p.name == plan), None)
    if not matching_plan:
        raise ValueError(f"Plan '{plan}' not found in offering '{offering}'")
    return matching_plan


def get_client(module):
    return AuthenticatedClient(
        base_url=module.params["api_url"],
        token=module.params["access_token"],
        prefix="Token",
        raise_on_unexpected_status=True,
    )


def get_os_instance(client, instance_name, project_name=None):
    if is_uuid_like(instance_name):
        return openstack_instances_retrieve.sync(client=client, uuid=instance_name)
    if project_name:
        kwargs = {"project_name": project_name}
    else:
        kwargs = {}
    instances = openstack_instances_list.sync(
        client=client, name=instance_name, **kwargs
    )
    if not instances:
        raise ObjectNotFoundError(f"Instance with name '{instance_name}' not found")
    return instances[0]
