#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility

from ansible.module_utils.basic import AnsibleModule
from waldur_api_client.types import UNSET
from waldur_api_client.client import AuthenticatedClient
from waldur_api_client.models.core_states import CoreStates
from waldur_api_client.models.open_stack_sub_net import OpenStackSubNet
from ansible_waldur_module.exceptions import (
    ResourceError,
    ObjectNotFoundError,
    ObjectStateError,
)
from ansible_waldur_module.utils import (
    get_client,
    is_uuid_like,
    waldur_resource_argument_spec,
)
from waldur_api_client.errors import UnexpectedStatus
from waldur_api_client.api.openstack_subnets import (
    openstack_subnets_retrieve,
    openstack_subnets_update,
    openstack_subnets_connect,
    openstack_subnets_disconnect,
    openstack_subnets_unlink,
)
from waldur_api_client.api.openstack_networks import (
    openstack_networks_create_subnet,
    openstack_networks_retrieve,
)
from waldur_api_client.models.open_stack_sub_net_request import OpenStackSubNetRequest
import time

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_os_subnet
short_description: The creation and management of OpenStack subnets
version_added: 0.1
description:
  - "Manage OpenStack subnets"
requirements:
  - "python = 3.8"
  - "waldur-api-client"
options:
  access_token:
    description:
      - An access token which has permissions to create and modify a subnet.
    required: true
  api_url:
    description:
      - Fully qualified URL to the Waldur.
    required: true
  subnet_uuid:
    description:
      - Unique identifier for subnet
  network_uuid:
    description:
      - Unique identifier of the network to associate with the subnet
  cidr:
    description:
      - The CIDR notation for the subnet
  gateway_ip
    description:
      - Specific IP address to use as the gateway
  disable_gateway:
    description:
      - Disable the gateway for a subnet
  allocation_pools
    description:
      - Allocation pool IP addresses for the subnet
  dns_nameservers
    description:
      - DNS nameservers for the subnet
  connect_subnet
    description:
    - Connect subnet
  disconnect_subnet
    description:
    - Disconnect subnet
  unlink_subnet:
    description:
    - Delete subnet from the database without scheduling operations on backend.
  state
    choices:
    - present
    - absent
    description:
      - Should the resource be present or absent

"""
EXAMPLES = """
- name: Connect a subnet to a router in a network
  hosts: localhost
  tasks:
    - name: connect subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        connect_subnet: True

- name: Disconnect a subnet from the router
  hosts: localhost
  tasks:
    - name: disconnect subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        disconnect_subnet: True

- name: Unlink a subnet
  hosts: localhost
  tasks:
    - name: destroy subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        unlink_subnet: True

- name: Update a subnet
  hosts: localhost
  tasks:
    - name: update subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        name: vanessa-nutrition-subnet
        gateway_ip: 192.168.42.2

"""


def wait_for_subnet(
    client: AuthenticatedClient, network_uuid, interval: int, timeout: int
):
    waited = 0
    while waited < timeout:
        network = openstack_networks_retrieve.sync(
            client=client,
            uuid=network_uuid,
        )
        if not network:
            raise ObjectNotFoundError("Network not found")
        if network.state == CoreStates.ERRED:
            raise ObjectStateError("Network is in an erred state")
        if network.state == CoreStates.OK:
            return True
        time.sleep(interval)
        waited += interval
    raise TimeoutError("Subnet creation timed out")


def fields_match(subnet: OpenStackSubNet, local_fields: dict) -> bool:
    for field, value in local_fields.items():
        current_value = getattr(subnet, field)
        if current_value != value:
            return False
    return True


def send_request_to_waldur(client: AuthenticatedClient, module):
    has_changed = False
    subnet_uuid = module.params.get("subnet_uuid")
    name = module.params.get("name")
    network_uuid = module.params.get("network_uuid")
    cidr = module.params.get("cidr")
    gateway_ip = module.params.get("gateway_ip")
    disable_gateway = module.params.get("disable_gateway")
    allocation_pools = module.params.get("allocation_pools")
    dns_nameservers = module.params.get("dns_nameservers")
    connect_subnet = module.params.get("connect_subnet")
    disconnect_subnet = module.params.get("disconnect_subnet")
    unlink_subnet = module.params.get("unlink_subnet")
    state = module.params.get("state")
    wait = module.params.get("wait")
    interval = module.params.get("interval")
    timeout = module.params.get("timeout")

    subnet = None
    present = state == "present"
    if subnet_uuid:
        if not is_uuid_like(subnet_uuid):
            raise ValueError("Invalid subnet UUID format")
        subnet = openstack_subnets_retrieve.sync(
            client=client,
            uuid=subnet_uuid,
        )
    if subnet:
        if present:
            if connect_subnet:
                openstack_subnets_connect.sync_detailed(
                    client=client,
                    uuid=subnet_uuid,
                )
                has_changed = True
            elif disconnect_subnet:
                openstack_subnets_disconnect.sync_detailed(
                    client=client,
                    uuid=subnet_uuid,
                )
                has_changed = True
            elif unlink_subnet:
                openstack_subnets_unlink.sync_detailed(
                    client=client,
                    uuid=subnet_uuid,
                )
                has_changed = True
            else:
                local_fields = {
                    "name": name,
                    "gateway_ip": gateway_ip,
                    "disable_gateway": disable_gateway,
                    "dns_nameservers": dns_nameservers,
                }
                if fields_match(subnet, local_fields):
                    has_changed = False
                else:
                    openstack_subnets_update.sync(
                        client=client,
                        uuid=subnet_uuid,
                        body=OpenStackSubNetRequest(
                            name=name or subnet.name,
                            gateway_ip=gateway_ip or subnet.gateway_ip,
                            disable_gateway=disable_gateway or subnet.disable_gateway,
                            dns_nameservers=dns_nameservers or subnet.dns_nameservers,
                        ),
                    )
                    has_changed = True

    else:
        if present:
            if not is_uuid_like(network_uuid):
                raise ValueError("Invalid network UUID format")
            subnet = openstack_networks_create_subnet.sync(
                client=client,
                uuid=network_uuid,
                body=OpenStackSubNetRequest(
                    allocation_pools=allocation_pools or UNSET,
                    dns_nameservers=dns_nameservers or UNSET,
                    cidr=cidr or UNSET,
                    disable_gateway=disable_gateway or UNSET,
                    gateway_ip=gateway_ip or UNSET,
                    name=name,
                ),
            )
            if wait:
                wait_for_subnet(client, network_uuid, interval, timeout)
            has_changed = True
    return has_changed


def main():
    fields = waldur_resource_argument_spec(
        subnet_uuid=dict(type="str"),
        name=dict(type="str", required=False),
        network_uuid=dict(type="str", required=False),
        cidr=dict(type="str", required=False),
        allocation_pools=dict(type="str", required=False),
        dns_nameservers=dict(type="list", required=False),
        disable_gateway=dict(type="str", required=False),
        gateway_ip=dict(type="str", required=False),
        connect_subnet=dict(type="bool", required=False),
        disconnect_subnet=dict(type="bool", required=False),
        unlink_subnet=dict(type="bool", required=False),
    )
    module = AnsibleModule(
        argument_spec=fields,
    )

    client = get_client(module)

    gateway_ip = module.params.get("gateway_ip")
    disable_gateway = module.params.get("disable_gateway")

    try:
        has_changed = send_request_to_waldur(client, module)
    except (UnexpectedStatus, ValueError, TimeoutError, ResourceError) as e:
        module.fail_json(msg=str(e))
    if gateway_ip:
        if disable_gateway is True:
            module.fail_json(
                msg="Gateway IP cannot be set while disable_gateway is True"
            )
    if disable_gateway is False:
        if not gateway_ip:
            module.fail_json(msg="Gateway ip must be set or gateway must be disabled")
    else:
        module.exit_json(changed=has_changed)


if __name__ == "__main__":
    main()
