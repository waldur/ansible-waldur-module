#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from waldur_api_client import AuthenticatedClient
from waldur_api_client.api.openstack_security_groups import (
    openstack_security_groups_list,
)
from waldur_api_client.errors import UnexpectedStatus
from waldur_api_client.api.openstack_tenants import openstack_tenants_list

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_os_security_group_gather_facts
short_description: Get OpenStack tenant security group
version_added: 0.1
description:
  - "Get OpenStack tenant security group"
requirements:
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
  name:
    description:
      - The name of the security group.
    required: false
  tenant:
    description:
      - The name of the tenant.
    required: true
"""

EXAMPLES = """
- name: get security group
  hosts: localhost
  tasks:
    - name: get security group
      waldur_os_security_group_gather_facts:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        tenant: VPC #1
        name: classic-web

- name: list tenant security groups
  hosts: localhost
  tasks:
    - name: list all security groups belonging to the tenant
      waldur_os_security_group_gather_facts:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        tenant: VPC #1
"""


def send_request_to_waldur(client, module):
    tenant = module.params["tenant"]
    name = module.params["name"]
    tenants_list = openstack_tenants_list.sync(
        client=client,
        name=tenant,
    )

    security_groups = openstack_security_groups_list.sync(
        client=client,
        tenant_uuid=tenants_list[0].uuid,
    )

    if name:
        matching_groups = [group for group in security_groups if group.name == name]
        if not matching_groups:
            module.fail_json(msg=f"Security group with name '{name}' not found")
        return matching_groups

    return [group.to_dict() for group in security_groups]


def main():
    fields = dict(
        api_url=dict(required=True, type="str"),
        access_token=dict(required=True, type="str", no_log=True),
        name=dict(type="str", required=False),
        tenant=dict(type="str", required=True),
    )
    module = AnsibleModule(argument_spec=fields)

    client = AuthenticatedClient(
        base_url=module.params["api_url"],
        token=module.params["access_token"],
    )

    try:
        security_groups = send_request_to_waldur(client, module)
    except UnexpectedStatus as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(security_groups=security_groups)


if __name__ == "__main__":
    main()
