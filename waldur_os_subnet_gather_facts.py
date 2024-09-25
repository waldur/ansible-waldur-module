#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from waldur_client import (
    WaldurClientException,
    waldur_client_from_module,
    waldur_full_argument_spec,
)

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_os_subnet_gather_facts
short_description: Get OpenStack tenant subnet
version_added: 0.1
description:
  - "Get subnets belonging to an OpenStack tenant"
requirements:´
  - "python = 3.8"
  - "requests"
  - "python-waldur-client"
options:
  access_token:
    description:
      - An access token which has permission to read a security group.
    required: true
  api_url:
    description:
      - Fully qualified URL to the Waldur.
    required: true
  tenant_uuid:
    description:
      - The uuid of the tenant.
    required: false
  subnet_uuid:
    description:
      - The uuid of the subnet.
    required: true
"""

EXAMPLES = """
- name: get subnet
  hosts: localhost
  tasks:
    - name: get subnet
      waldur_os_subnet_gather_facts:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        tenant: VPC #1
        name: waldur-dev-subnet-1

- name: list tenant subnets
  hosts: localhost
  tasks:
    - name: list all subnets belonging to the tenant
      waldur_os_subnet_gather_facts:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        tenant: waldur-dev-subnet-1
"""


def send_request_to_waldur(client, module):
    tenant_uuid = module.params["tenant_uuid"]
    subnet_uuid = module.params["subnet_uuid"]
    if subnet_uuid:
        return [client.get_subnet_by_uuid(subnet_uuid)]
    else:
        return client.list_tenant_subnets(tenant_uuid)


def main():
    fields = waldur_full_argument_spec(
        subnet_uuid=dict(required=False, type="str"),
        tenant_uuid=dict(required=True, type="str"),
    )
    module = AnsibleModule(argument_spec=fields)

    client = waldur_client_from_module(module)

    try:
        subnets = send_request_to_waldur(client, module)
    except WaldurClientException as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(subnets=subnets)


if __name__ == "__main__":
    main()
