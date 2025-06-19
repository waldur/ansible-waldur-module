#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
import time
from ansible_waldur_module.exceptions import ResourceError, ResourceStateError
from waldur_api_client.api.openstack_instances import (
    openstack_instances_list,
    openstack_instances_retrieve,
    openstack_instances_update_floating_ips,
)
from waldur_api_client.models.open_stack_instance_floating_i_ps_update_request import (
    OpenStackInstanceFloatingIPsUpdateRequest,
)
from waldur_api_client.errors import UnexpectedStatus
from ansible_waldur_module.utils import get_argument_spec
from waldur_api_client.models.open_stack_nested_floating_ip_request import (
    OpenStackNestedFloatingIPRequest,
)
from ansible_waldur_module.utils import get_client
from waldur_api_client.models.core_states import CoreStates

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_os_floating_ip
short_description: Assign floating IPs
version_added: 0.1
requirements:
  - "python = 3.8"
  - "requests"
  - "python-waldur-client"
options:
  access_token:
    description:
      - An access token which has permissions to create an OpenStack instances.
    required: true
  address:
    description:
      - IP address of the floating IP to be assigned to the instance.
        It is required if 'floating_ips' are not provided.
  api_url:
    description:
      - Fully qualified url to the Waldur.
    required: true
  floating_ips:
    description:
      - A list of floating IPs to be assigned to the instance.
        A floating IP consists of 'subnet' and 'address'.
        It is required if 'floating_ips' are not provided.
  subnet:
    description:
      - A subnet to be assigned to the instance.
        It is required if 'floating_ips' are not provided.
  instance:
    description:
      - The name of the virtual machine to assign floating IPs to.
    required: true
  interval:
    default: 20
    description:
      - An interval of the instance state polling.
  timeout:
    default: 600
    description:
      - The maximum amount of seconds to wait until the floating IP is assigned to instance.
  wait:
    default: true
    description:
      - A boolean value that defines whether client has to wait until the floating IP is assigned to instance.
"""

EXAMPLES = """
- name: assign multiple floating IPs
  hosts: localhost
  tasks:
    - name: assign single floating IP
      waldur_os_floating_ip:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000
        instance: VM #1
        floating_ips:
            - address: 10.30.201.18
              subnet: vpc-1-tm-sub-net
            - address: 10.30.201.177
              subnet: vpc-2-tm-sub-net

- name: assign floating IP
  hosts: localhost
  tasks:
    - name: assign single floating IP
      waldur_os_floating_ip:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000
        instance: VM #3
        address: 10.30.201.19
        subnet: vpc-3-tm-sub-net

- name: detach floating IP
  hosts: localhost
  tasks:
    - name: detach floating IP
      waldur_os_floating_ip:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000
        instance: VM #3
        state: absent
"""


def is_instance_ready(client, instance_uuid):
    instance = openstack_instances_retrieve.sync(
        client=client,
        uuid=instance_uuid,
    )
    if instance.state == CoreStates.ERRED:
        raise ResourceStateError(
            f"Instance is in erred state: {instance.error_message}"
        )
    return instance.state == CoreStates.OK


def wait_for_instance(client, instance_uuid, interval=20, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_instance_ready(client, instance_uuid):
            return True
        time.sleep(interval)

    raise ResourceStateError(f"Instance '{instance_uuid}' has not reached stable state")


def get_os_instance_by_name(client, instance_name, module):
    try:
        instances = openstack_instances_list.sync(
            client=client,
            name=instance_name,
        )
    except UnexpectedStatus as e:
        module.fail_json(msg=str(e))
    if not instances:
        module.fail_json(msg=f"Instance with name '{instance_name}' not found")
    return instances[0]


def main():
    fields = get_argument_spec(
        instance=dict(type="str"),
        floating_ips=dict(type="list"),
        address=dict(type="str"),
        subnet=dict(type="str"),
        state=dict(default="present", choices=["absent", "present"]),
    )
    required_together = [["address", "subnet"]]
    mutually_exclusive = [["floating_ips", "subnet"], ["floating_ips", "address"]]
    required_if = [
        ("state", "present", ("floating_ips", "subnet"), True),
    ]
    module = AnsibleModule(
        argument_spec=fields,
        required_together=required_together,
        mutually_exclusive=mutually_exclusive,
        required_if=required_if,
    )

    present = module.params["state"] == "present"

    client = get_client(module)

    if present:
        floating_ips = module.params.get("floating_ips") or [
            {
                "address": module.params["address"],
                "subnet": module.params["subnet"],
            }
        ]
        if not floating_ips or not isinstance(floating_ips, list):
            module.fail_json(msg="'floating_ips' must be a non-empty list.")

        # Create the request body using the subnet directly from the input
        request = OpenStackInstanceFloatingIPsUpdateRequest(
            floating_ips=[
                OpenStackNestedFloatingIPRequest(subnet=floating_ip["subnet"])
                for floating_ip in floating_ips
            ]
        )

    else:
        request = OpenStackInstanceFloatingIPsUpdateRequest(floating_ips=[])

    try:
        instance = get_os_instance_by_name(client, module.params["instance"], module)
        response = openstack_instances_update_floating_ips.sync_detailed(
            client=client, uuid=instance.uuid, body=request
        )
        if module.params["wait"]:
            wait_for_instance(
                client,
                instance.uuid,
                timeout=module.params["timeout"],
                interval=module.params["interval"],
            )
    except (UnexpectedStatus, ResourceError, TimeoutError) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(meta=response)


if __name__ == "__main__":
    main()
