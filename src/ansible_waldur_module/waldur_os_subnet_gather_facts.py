#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from ansible_waldur_module.utils import get_argument_spec, get_client, is_uuid_like
from waldur_api_client.api.openstack_subnets import openstack_subnets_list
from waldur_api_client.api.openstack_subnets import openstack_subnets_retrieve
from waldur_api_client.errors import UnexpectedStatus

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
  - "waldur-api-client"
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
        if not is_uuid_like(subnet_uuid):
            raise ValueError("Invalid subnet UUID format")
        subnet = openstack_subnets_retrieve.sync(
            client=client,
            uuid=subnet_uuid,
        )
        return [subnet.to_dict()] if subnet else []
    else:
        if not is_uuid_like(tenant_uuid):
            raise ValueError("Invalid tenant UUID format")
        subnets = openstack_subnets_list.sync(
            client=client,
            tenant_uuid=tenant_uuid,
        )
        return [subnet.to_dict() for subnet in subnets]


def main():
    fields = {
        "subnet_uuid": dict(required=False, type="str"),
        "tenant_uuid": dict(required=True, type="str"),
    }
    module = AnsibleModule(get_argument_spec(**fields))
    client = get_client(module)

    try:
        subnets = send_request_to_waldur(client, module)
    except (UnexpectedStatus, ValueError, TimeoutError) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(subnets=subnets)


if __name__ == "__main__":
    main()
