#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
import uuid
from waldur_api_client import AuthenticatedClient


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


def get_client(module):
    return AuthenticatedClient(
        base_url=module.params["api_url"],
        token=module.params["access_token"],
        prefix="Token",
        timeout=600,
        raise_on_unexpected_status=True,
    )
