#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from waldur_api_client import AuthenticatedClient
from waldur_api_client.api.marketplace_orders import marketplace_orders_create
from waldur_api_client.api.marketplace_public_offerings import (
    marketplace_public_offerings_list,
    marketplace_public_offerings_retrieve,
)
from waldur_api_client.api.openstack_volumes import (
    openstack_volumes_list,
    openstack_volumes_update,
)
from waldur_api_client.api.marketplace_resources import marketplace_resources_terminate
from waldur_api_client.models.resource_terminate_request import ResourceTerminateRequest
from waldur_api_client.api.openstack_volume_types import openstack_volume_types_list
from waldur_api_client.models.order_create import OrderCreate
from waldur_api_client.models.order_create_request import OrderCreateRequest
from waldur_api_client.errors import UnexpectedStatus
from waldur_api_client.models.open_stack_volume_request import OpenStackVolumeRequest
from waldur_api_client.api.openstack_volume_types import openstack_volume_types_retrieve
from waldur_api_client.api.marketplace_orders import marketplace_orders_retrieve
from ansible_waldur_module.utils import (
    waldur_resource_argument_spec,
    convert_to_mb,
    is_uuid_like,
    get_client,
    get_project,
)
from waldur_api_client.models.order_state import OrderState
import time
from ansible_waldur_module.exceptions import (
    ObjectStateError,
    ResourceError,
    ObjectNotFoundError,
)

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_marketplace_os_volume
short_description: Create/Update/Delete OpenStack volume via marketplace
version_added: 0.8
description:
  - "Create/Update/Delete OpenStack volume"
requirements:
  - "python = 3.8"
  - "waldur-api-client"
options:
  access_token:
    description:
      - An access token which has permissions to create a volume.
    required: true
  api_url:
    description:
      - Fully qualified URL to the Waldur.
    required: true
  description:
    description:
      - A description of the volume.
  interval:
    default: 20
    description:
      - An interval of the volume state polling.
  name:
    description:
      - The name of the volume.
    required: true
  project:
    description:
      - The name or id of the project to add volume to.
        It is required if is state is 'present'.
  offering:
    description:
      - The name or id of the marketplace offering.
        It is required if is state is 'present'.
  size:
    description:
      - The size of the volume in GBs.
        It is required if is state is 'present'.
  type:
    description:
      - UUID or name of volume type.
  state:
    choices:
      - present
      - absent
    default: present
    description:
      - Should the resource be present or absent.
  timeout:
    default: 600
    description:
      - The maximum amount of seconds to wait until the volume provisioning is finished.
  wait:
    default: true
    description:
      - A boolean value that defines whether client has to wait until the volume is provisioned.
"""

EXAMPLES = """
- name: add volume
  hosts: localhost
  tasks:
    - name: create volume
      waldur_marketplace_os_volume:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: test volume
        project: OpenStack Project
        offering: Volume in Tenant
        size: 40
        type: lvm
        state: present

- name: remove volume
  hosts: localhost
  tasks:
    - name: remove existing volume
      waldur_marketplace_os_volume:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: test volume
        project: OpenStack Project
        state: absent

- name: update volume
  hosts: localhost
  tasks:
    - name: update volume description
      waldur_marketplace_os_volume:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: test volume
        project: OpenStack Project
        description: do not delete this volume
"""


def wait_for_order_completion(client, order_uuid, timeout, interval):
    """Wait for order completion."""
    waited = 0
    while waited < timeout:
        order = marketplace_orders_retrieve.sync(client=client, uuid=order_uuid)
        if order and order.state == OrderState.DONE:
            return order
        elif order and order.state in [
            OrderState.ERRED,
            OrderState.REJECTED,
            OrderState.CANCELED,
        ]:
            raise ObjectStateError(f"Order failed: {order.error_message}")
        time.sleep(interval)
        waited += interval
    raise TimeoutError(f"Order {order_uuid} has not reached a valid state")


def find_existing_volume(client, name, project, module):
    """Find existing volume by name and project."""
    try:
        volumes = openstack_volumes_list.sync(
            client=client,
            name_exact=name,
            project_uuid=project.uuid,
        )
        if volumes and len(volumes) > 0:
            return volumes[0]
        return None
    except UnexpectedStatus as e:
        module.fail_json(msg=str(e))


def get_volume_type(client, volume_type):
    if is_uuid_like(volume_type):
        return openstack_volume_types_retrieve.sync(client=client, uuid=volume_type)
    volume_types = openstack_volume_types_list.sync(
        client=client, name_exact=volume_type
    )
    if not volume_types:
        raise ValueError(f"Volume type '{volume_type}' not found")
    return volume_types[0]


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
        raise ObjectNotFoundError(f"Offering '{offering}' not found")
    return offerings[0]


def send_request_to_waldur(client, module):
    has_changed = False
    name = module.params["name"]
    project = module.params["project"]
    offering = module.params["offering"]
    size = module.params["size"]
    wait = module.params["wait"]
    timeout = module.params["timeout"]
    interval = module.params["interval"]
    volume_type_name_or_uuid = module.params["type"]
    description = module.params.get("description", "")
    project = get_project(client, project)
    # Check if volume already exists
    existing_volume = find_existing_volume(client, name, project, module)
    is_present = module.params["state"] == "present"
    if existing_volume:
        if is_present:
            if existing_volume.description != description:
                try:
                    update_request = OpenStackVolumeRequest(
                        name=name,
                        description=description,
                    )
                    openstack_volumes_update.sync(
                        client=client, uuid=existing_volume.uuid, body=update_request
                    )
                    has_changed = True
                except UnexpectedStatus as e:
                    module.fail_json(
                        msg=f"Failed to update volume description: {str(e)}"
                    )
        else:
            try:
                marketplace_resources_terminate.sync(
                    client=client,
                    uuid=existing_volume.marketplace_resource_uuid,
                    body=ResourceTerminateRequest(),
                )
                has_changed = True
            except UnexpectedStatus as e:
                module.fail_json(msg=f"Failed to unlink volume: {str(e)}")
    elif is_present:
        try:
            size_mb = convert_to_mb(size)
        except ValueError as e:
            module.fail_json(msg=f"Invalid size value: {str(e)}")
        attributes = {"name": name, "description": description, "size": size_mb}
        offering = get_offering(client, offering)
        volume_type = get_volume_type(client, volume_type_name_or_uuid)

        if volume_type:
            attributes["type"] = volume_type.url
        order_request = OrderCreateRequest(
            offering=offering.url,
            project=project.url,
            attributes=attributes,
            accepting_terms_of_service=True,
        )

        order_create_response: OrderCreate | None = marketplace_orders_create.sync(
            client=client,
            body=order_request,
        )
        if not order_create_response:
            raise ObjectNotFoundError("Error creating marketplace order")

        order_details = marketplace_orders_retrieve.sync(
            client=client,
            uuid=order_create_response.uuid,
        )
        if order_details is None:
            raise ObjectNotFoundError("Error retrieving order details")

        if wait:
            wait_for_order_completion(client, order_details.uuid, timeout, interval)

        has_changed = True

    return has_changed


def main():
    fields = waldur_resource_argument_spec(
        project=dict(type="str", default=None),
        offering=dict(type="str", default=None),
        size=dict(type="int", default=None),
        type=dict(type="str", default=None),
    )
    module = AnsibleModule(argument_spec=fields)

    state = module.params["state"]
    project = module.params["project"]
    offering = module.params["offering"]
    size = module.params["size"]

    if state == "present":
        if not project:
            module.fail_json(
                msg="Parameter 'project' is required if state == 'present'"
            )
        if not offering:
            module.fail_json(
                msg="Parameter 'offering' is required if state == 'present'"
            )
        if not size:
            module.fail_json(msg="Parameter 'size' is required if state == 'present'")

    client = get_client(module)

    try:
        has_changed = send_request_to_waldur(client, module)
    except (
        UnexpectedStatus,
        ObjectStateError,
        TimeoutError,
        ResourceError,
    ) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(changed=has_changed)


if __name__ == "__main__":
    main()
