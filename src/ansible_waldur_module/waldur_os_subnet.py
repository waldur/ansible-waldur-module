#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility

from ansible.module_utils.basic import AnsibleModule
from waldur_client import (
    WaldurClient,
    WaldurClientException,
    waldur_client_from_module,
    waldur_resource_argument_spec,
)

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
  - "requests"
  - "python-waldur-client"
options:
  access_token:
    description:
      - An access token which has permissions to create and modify a subnet.
    required: true
  api_url:
    description:
      - Fully qualified URL to the Waldur.
    required: true
  uuid:
    description:
      - Unique identifier for subnet
  tenant:
    description:
      - The name or uuid of the tenant that the subnet should be connected to
    required: true
  project:
    description:
      - The name or uuid of the project that the subnet is apart of
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
  enable_dhcp
    description:
      - Enable dhcp on the subnet
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
        project: feline-suppliment-sourcer
        connect_subnet: True

- name: Disconnect a subnet from the router
  hosts: localhost
  tasks:
    - name: disconnect subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        project: feline-suppliment-sourcer
        disconnect_subnet: True

- name: Unlink a subnet
  hosts: localhost
  tasks:
    - name: destroy subnet
      waldur_os_subnet:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        uuid: 935c8841fd1644228a9d1463e8693650
        project: feline-suppliment-sourcer
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
        project: feline-suppliment-sourcer
        gateway_ip: 192.168.42.2

"""


def compare_fields(checked_fields, local_fields):
    try:
        field_diff = {
            k: checked_fields[k]
            for k, v in checked_fields
            if k in local_fields
            if local_fields[k, v] != checked_fields[k, v]
        }
        if field_diff:
            return True
        else:
            return False
    except ValueError:
        return False


def send_request_to_waldur(client: WaldurClient, module):
    has_changed = False
    subnet_uuid = module.params.get("subnet_uuid")
    name = module.params.get("name")
    tenant = module.params.get("tenant")
    project = module.params.get("project")
    network_uuid = module.params.get("network_uuid")
    cidr = module.params.get("cidr")
    gateway_ip = module.params.get("gateway_ip")
    disable_gateway = module.params.get("disable_gateway")
    allocation_pools = module.params.get("allocation_pools")
    enable_dhcp = module.params.get("enable_dhcp")
    dns_nameservers = module.params.get("dns_nameservers")
    connect_subnet = module.params.get("connect_subnet")
    disconnect_subnet = module.params.get("disconnect_subnet")
    unlink_subnet = module.params.get("unlink_subnet")
    state = module.params.get("state")

    subnet = None
    present = state == "present"

    subnet = client.get_subnet_by_uuid(subnet_uuid)
    if subnet:
        if present:
            checked_fields = {
                k: v
                for k, v in subnet.items()
                if k
                in [
                    "name",
                    "tenant",
                    "gateway_ip",
                    "disable_gateway",
                    "enable_dhcp",
                    "dns_nameservers",
                    "connect_subnet",
                    "disconnect_subnet",
                    "unlink_subnet",
                ]
            }
            local_fields = [
                name,
                tenant,
                gateway_ip,
                disable_gateway,
                enable_dhcp,
                dns_nameservers,
                connect_subnet,
                disconnect_subnet,
                unlink_subnet,
            ]

            if compare_fields(checked_fields, local_fields):
                has_changed = False
            else:
                if not compare_fields(checked_fields, local_fields):
                    client.update_subnet(
                        uuid=subnet_uuid,
                        name=name,
                        tenant=tenant,
                        gateway_ip=gateway_ip,
                        disable_gateway=disable_gateway,
                        enable_dhcp=enable_dhcp,
                        dns_nameservers=dns_nameservers,
                        connect_subnet=connect_subnet,
                        disconnect_subnet=disconnect_subnet,
                        unlink_subnet=unlink_subnet,
                    )
                    has_changed = True

    else:
        if present:
            subnet = client.create_subnet(
                name=name,
                tenant=tenant,
                project=project,
                network_uuid=network_uuid,
                cidr=cidr,
                allocation_pools=allocation_pools,
                enable_dhcp=enable_dhcp,
                dns_nameservers=dns_nameservers,
                disable_gateway=disable_gateway,
                gateway_ip=gateway_ip,
                wait=module.params["wait"],
                interval=module.params["interval"],
                timeout=module.params["timeout"],
            )
        has_changed = True

    return subnet, has_changed


def main():
    fields = waldur_resource_argument_spec(
        subnet_uuid=dict(type="str"),
        name=dict(type="str", required=False),
        tenant=dict(type="str", required=False),
        project=dict(type="str", required=False),
        network_uuid=dict(type="str", required=False),
        cidr=dict(type="str", required=False),
        allocation_pools=dict(type="str", required=False),
        enable_dhcp=dict(type="bool", required=False, default=True),
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

    client = waldur_client_from_module(module)

    gateway_ip = module.params.get("gateway_ip")
    disable_gateway = module.params.get("gateway_ip")

    try:
        has_changed = send_request_to_waldur(client, module)
    except WaldurClientException as e:
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
