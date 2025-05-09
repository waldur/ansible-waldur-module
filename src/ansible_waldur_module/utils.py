#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
import uuid


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
