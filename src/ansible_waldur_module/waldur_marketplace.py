#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
import yaml
from ansible.module_utils.basic import AnsibleModule, to_text
from waldur_api_client.api.marketplace_orders import marketplace_orders_create
from waldur_api_client.models.order_create_request import OrderCreateRequest
from waldur_api_client.models.order_create_request_limits import (
    OrderCreateRequestLimits,
)
from waldur_api_client.errors import UnexpectedStatus
import httpx
from ansible_waldur_module.utils import (
    get_argument_spec,
    get_project,
    get_offering,
    get_plan,
    get_client,
)

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_marketplace
short_description: Create order in Waldur Marketplace.
version_added: 0.1
description:
  - Create marketplace order via Waldur API.
requirements:
  - python = 3.8
  - waldur-api-client
options:
  access_token:
    description:
      - An access token which has permissions to create a marketplace order.
    required: true
  api_url:
    description:
      - Fully qualified url to the Waldur.
    required: true
  project:
    required: true
    description:
      - The name or UUID of the project to add an order to.
  offering:
    required: true
    description:
      - The name or UUID of the offering to add an order to.
  plan:
    required: true
    description:
      - The name or UUID of the order plan.
  attributes:
    default: None
    description:
      - order attributes or path to JSON or YAML file with order attributes.
  limits:
    default: None
    description:
      - order limits or path to JSON or YAML file with order limits.
"""

EXAMPLES = """
- name: Create a new marketplace order.
  hosts: localhost
  gather_facts: False
  tasks:
    - name: Add order
      waldur_marketplace:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: Project
        offering: 7887745b83c74fc38d695ed58648ea20
        plan: 4d50f6584ed84df3b6c83075044fd284

- name: Create a new marketplace order using names.
  hosts: localhost
  gather_facts: False
  tasks:
    - name: Add order
      waldur_marketplace:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: Project
        offering: Offering name
        plan: Plan name

- name: Create a new marketplace order using attributes as file path.
  hosts: localhost
  gather_facts: False
  tasks:
    - name: Add order
      waldur_marketplace:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: Project
        offering: Offering name
        plan: Plan name
        attributes: /home/user/attributes

- name: Create a new marketplace order using attributes as dictionary.
  hosts: localhost
  gather_facts: False
  tasks:
    - name: Add order
      waldur_marketplace:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: Project
        offering: Offering name
        plan: Plan name
        attributes:
          name: my name
"""


def send_request_to_waldur(client, module):
    project = get_project(client, module.params["project"])
    offering = get_offering(client, module.params["offering"])
    plan = get_plan(client, module.params["plan"], module.params["offering"])
    attributes = module.params.get("attributes")
    limits = module.params.get("limits")

    def get_file_content(path):
        if path:
            value = yaml.safe_load(path)
            if isinstance(value, str):
                with open(value) as f:
                    return yaml.safe_load(f.read())
            else:
                return value

    attributes = get_file_content(attributes) or {}
    limits = get_file_content(limits) or {}
    limits_obj = OrderCreateRequestLimits.from_dict(limits)
    try:
        order_request = OrderCreateRequest(
            offering=offering.url,
            project=project.url,
            plan=plan.url,
            attributes=attributes,
            limits=limits_obj,
            accepting_terms_of_service=True,
        )

        response = marketplace_orders_create.sync(
            client=client,
            body=order_request,
        )
    except (UnexpectedStatus, ValueError) as e:
        module.fail_json(msg=str(e))

    return response.to_dict(), True


def main():
    module = AnsibleModule(
        argument_spec=get_argument_spec(
            project=dict(type="str", required=True),
            offering=dict(type="str", required=True),
            plan=dict(type="str", required=True),
            attributes=dict(type="str", default=None),
            limits=dict(type="str", default=None),
        )
    )

    client = get_client(module)
    try:
        order, has_changed = send_request_to_waldur(client, module)
    except (IOError, OSError) as e:
        module.fail_json(msg="Unable to open file: %s" % to_text(e))
    except (UnexpectedStatus, ValueError, httpx.TimeoutException) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(order=order, changed=has_changed)


if __name__ == "__main__":
    main()
