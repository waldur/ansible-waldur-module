#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule

from waldur_api_client.api.openstack_instances import openstack_instances_list
from waldur_api_client.errors import UnexpectedStatus
from ansible_waldur_module.utils import (
    get_argument_spec,
    is_uuid_like,
    get_project,
    get_client,
)

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_marketplace_os_get_instance
short_description: Get existing OpenStack instance
version_added: 0.1
description:
  - Get an OpenStack instance
requirements:
  - python = 3.8
  - requests
  - python-waldur-client
options:
  access_token:
    description:
      - An access token which has permissions to create an OpenStack instances.
    required: true
  api_url:
    description:
      - Fully qualified url to the Waldur.
    required: true
  name:
    description:
      - The name or UUID of existing OpenStack instance.
    required: true
  project:
    description:
      - The name or UUID of the project where instance is created.
    required: true
"""

EXAMPLES = """
- name: Get an OpenStack instance
  hosts: localhost
  tasks:
    - name: get instance
      waldur_marketplace_os_get_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: Warehouse instance
        project: OpenStack Project
"""


def main():
    fields = {
        "name": {"required": True, "type": "str"},
        "project": {"required": False, "type": "str"},
    }
    module = AnsibleModule(argument_spec=get_argument_spec(**fields))

    client = get_client(module)
    try:
        if is_uuid_like(module.params["project"]):
            project_uuid = module.params["project"]
        else:
            project = get_project(client, module.params["project"])
            project_uuid = project.uuid
        kwargs = (
            {"uuid": module.params["name"]}
            if is_uuid_like(module.params["name"])
            else {"name": module.params["name"]}
        )
        instances = openstack_instances_list.sync(
            client=client,
            **kwargs,
            project=project_uuid,
        )
        # Convert the instance to a dict for Ansible
        instance = instances[0].to_dict()
        module.exit_json(instance=instance)
    except (UnexpectedStatus, ValueError, IndexError) as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
