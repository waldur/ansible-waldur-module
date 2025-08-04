#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from ansible_waldur_module.exceptions import (
    ObjectNotFoundError,
    ResourceMultipleFoundError,
    ObjectStateError,
)
from waldur_api_client import AuthenticatedClient
from waldur_api_client.api.openstack_instances import (
    openstack_instances_list,
    openstack_instances_retrieve,
    openstack_instances_update_security_groups,
    openstack_instances_update_ports,
    openstack_instances_stop,
)
from waldur_api_client.api.marketplace_resources import (
    marketplace_resources_list,
    marketplace_resources_terminate,
)
from waldur_api_client.errors import UnexpectedStatus
from ansible_waldur_module.utils import (
    get_argument_spec,
    get_project,
    get_offering,
    is_uuid_like,
    get_client,
)
from waldur_api_client.models.core_states import CoreStates
from waldur_api_client.models.resource_terminate_request import ResourceTerminateRequest
from waldur_api_client.models.open_stack_instance_security_groups_update_request import (
    OpenStackInstanceSecurityGroupsUpdateRequest,
)
from waldur_api_client.models.open_stack_instance_ports_update_request import (
    OpenStackInstancePortsUpdateRequest,
)
from waldur_api_client.models.open_stack_nested_port_request import (
    OpenStackNestedPortRequest,
)
from waldur_api_client.api.marketplace_orders import (
    marketplace_orders_create,
    marketplace_orders_approve_by_consumer,
)
from waldur_api_client.models.order_create_request import OrderCreateRequest
from waldur_api_client.models.order_create import OrderCreate
from waldur_api_client.models.public_offering_details import PublicOfferingDetails
import time
from waldur_api_client.api.openstack_flavors import (
    openstack_flavors_list,
    openstack_flavors_retrieve,
)
from waldur_api_client.api.openstack_images import (
    openstack_images_list,
    openstack_images_retrieve,
)
from waldur_api_client.api.openstack_volume_types import (
    openstack_volume_types_list,
    openstack_volume_types_retrieve,
)
from waldur_api_client.api.openstack_security_groups import (
    openstack_security_groups_list,
    openstack_security_groups_retrieve,
)
from waldur_api_client.api.openstack_server_groups import (
    openstack_server_groups_list,
    openstack_server_groups_retrieve,
)
from waldur_api_client.api.keys import keys_list, keys_retrieve
from waldur_api_client.models.openstack_flavors_list_o_item import (
    OpenstackFlavorsListOItem,
)


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_marketplace_os_instance
short_description: Create, update or delete OpenStack instance via marketplace
version_added: 0.8
description:
  - Create, update or delete OpenStack compute instance via Waldur API.
requirements:
  - python = 3.8
  - waldur-api-client
options:
  access_token:
    description:
      - An access token which has permissions to create an OpenStack instances.
    required: true
  api_url:
    description:
      - Fully qualified url to the Waldur.
    required: true
  data_volume_size:
    description:
      - The size of the data volume in GB. Data volume is not created if value is empty.
  data_volume_type:
    description:
      - UUID or name of data volume type.
  delete_volumes:
    description:
      - If true, delete volumes when deleting instance.
    default: true
  flavor:
    description:
      - The name or id of the flavor to use.
        If this is not declared, flavor_min_cpu and/or flavor_min_ram must be declared.
  flavor_min_cpu:
    description:
      - The minimum cpu count.
  flavor_min_ram:
    description:
      - The minimum ram size (MB).
  floating_ip:
    description:
      - An id or address of the existing floating IP to use.
        Not assigned if not specified. Use `auto` to allocate new floating IP or reuse available one.
        It is required if a `networks` parameter is not provided.
  image:
    description:
      - The name or id of the image to use.
        It is required if is state is 'present'.
  interval:
    default: 20
    description:
      - An interval of the instance state polling.
  name:
    description:
      - The name of the new OpenStack instance or UUID for existing instance.
    required: true
  networks:
    description:
      - A list of networks an instance has to be attached to.
        A network object consists of 'floating_ip' and 'subnet' fields.
        It is required if neither 'floating_ip' nor 'subnet' provided.
  project:
    description:
      - The name or UUID of the project to add an instance to.
        It is required if is state is 'present'.
  offering:
    description:
      - The name or UUID of the marketplace offering.
        It is  required if is state is 'present'.
  release_floating_ips:
    description:
      - When state is absent and this option is true, any floating IP
        associated with the instance will be deleted along with the instance.
    default: true
  security_groups:
    default: default
    description:
      - A list of ids or names of security groups to apply to the newly created instance.
  ssh_key:
    description:
      - The name or id of the SSH key to attach to the newly created instance.
  state:
    choices:
      - present
      - absent
    default: present
    description:
      - Should the resource be present or absent.
  subnet:
    description:
      - The subnet name or id or list of subnet names or subnet ids.
        It is required if a `networks` parameter is not provided.
  system_volume_size:
    description:
      - The size of the system volume in GBs.
        It is required if is state is 'present'.
  system_volume_type:
    description:
      - UUID or name of system volume type.
  timeout:
    default: 600
    description:
      - The maximum amount of seconds to wait until the instance provisioning is finished.
  user_data:
    description:
      - An additional data that will be added to the instance on provisioning.
  wait:
    default: true
    description:
      - A boolean value that defines whether client has to wait until the instance
      provisioning is finished.
"""

EXAMPLES = """
- name: provision a warehouse instance
  hosts: localhost
  tasks:
    - name: add instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        data_volume_size: 100
        data_volume_type: lvm
        flavor: m1.micro
        image: Ubuntu 16.04 x86_64
        name: Warehouse instance
        networks:
          - floating_ip: auto
            subnet: vpc-1-tm-sub-net
          - floating_ip: 192.101.13.124
            subnet: vpc-1-tm-sub-net-2
        project: OpenStack Project
        offering: Instance in Tenant
        security_groups:
          - web

- name: Provision instance with user data
  hosts: localhost
  tasks:
    - name: add instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        flavor: m1.micro
        floating_ip: auto
        image: CentOS 7 x86_64
        name: Build instance
        project: OpenStack Project
        offering: Instance in Tenant
        ssh_key: ssh1.pub
        subnet: vpc-1-tm-sub-net-2
        system_volume_size: 40
        system_volume_type: lvm
        user_data: |-
            #cloud-config
            chpasswd:
              list: |
                ubuntu:{{ default_password }}
              expire: False

- name: Trigger master instance
  hosts: localhost
  tasks:
    - name: add instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        flavor: m1.micro
        floating_ip: auto
        image: CentOS 7 x86_64
        name: Build instance
        project: OpenStack Project
        offering: Instance in Tenant
        ssh_key: ssh1.pub
        subnet: vpc-1-tm-sub-net-2
        system_volume_size: 40
        wait: false

- name: Find flavor by CPU and RAM parameters
  hosts: localhost
  tasks:
    - name: add instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        data_volume_size: 100
        flavor_min_cpu: 2
        flavor_min_ram: 1024
        image: Ubuntu 16.04 x86_64
        name: Warehouse instance
        networks:
          - floating_ip: auto
            subnet: vpc-1-tm-sub-net
          - floating_ip: 192.101.13.124
            subnet: vpc-1-tm-sub-net-2
        project: OpenStack Project
        offering: Instance in Tenant
        security_groups:
          - web

- name: create OpenStack instance with predefined floating IP
  hosts: localhost
  tasks:
    - name: create instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: OpenStack Project
        offering: Instance in Tenant
        name: Warehouse instance
        image: CentOS 7
        flavor: m1.small
        subnet: vpc-1-tm-sub-net-2
        floating_ip: 1.1.1.1
        system_volume_size: 10

- name: delete existing OpenStack compute instance
  hosts: localhost
  tasks:
    - name: delete instance
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: OpenStack Project
        name: Warehouse instance
        state: absent

- name: update security groups of instance
  hosts: localhost
  tasks:
    - name: update security groups of mysql server
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: mysql-server
        project: OpenStack Project
        state: present
        security_groups:
          - ssh
          - icmp

- name: connect the instance to multiple subnets
  hosts: localhost
  tasks:
    - name: connect to multiple subnets
      waldur_marketplace_os_instance:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        project: OpenStack Project
        name: Warehouse instance
        subnet:
          - vpc-1-tm-sub-net-1
          - vpc-1-tm-sub-net-2
"""


def is_instance_ready(client, instance_uuid):
    instance = openstack_instances_retrieve.sync(
        client=client,
        uuid=instance_uuid,
    )
    if instance.state == CoreStates.ERRED:
        raise ObjectStateError(f"Instance is in erred state: {instance.error_message}")
    return instance.state == CoreStates.OK


def wait_for_instance(client, instance_uuid, interval=20, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_instance_ready(client, instance_uuid):
            return True
        time.sleep(interval)

    message = f"Instance '{instance_uuid}' has not reached stable state. Seconds passed: {timeout}"
    raise TimeoutError(message)


def get_instance_via_marketplace(client: AuthenticatedClient, name: str, project: str):
    project_obj = get_project(client, project)

    instance = None
    instance_name = name

    if is_uuid_like(name):
        instance = openstack_instances_retrieve.sync(client=client, uuid=name)
        instance_name = instance.name

    resources = marketplace_resources_list.sync(
        client=client,
        project_uuid=project_obj.uuid,
        name_exact=instance_name,
        offering_type="OpenStackTenant.Instance",
    )
    if not resources:
        raise ObjectNotFoundError(
            f"Marketplace resource '{instance_name}' not found in project '{project}'"
        )

    resource = resources[0]

    if instance is None:
        instances = openstack_instances_list.sync(
            client=client, project_uuid=project_obj.uuid, name_exact=instance_name
        )
        instance = instances[0] if instances else None
    return resource, instance


def get_flavor_url(client: AuthenticatedClient, flavor_identifier: str):
    """Get flavor URL from identifier (name or UUID)."""
    if is_uuid_like(flavor_identifier):
        flavor = openstack_flavors_retrieve.sync(client=client, uuid=flavor_identifier)
        if flavor is None:
            raise ObjectNotFoundError(
                f"Flavor with UUID '{flavor_identifier}' not found"
            )
        return flavor.url
    else:
        flavors = openstack_flavors_list.sync(
            client=client,
            name_exact=flavor_identifier,
        )
        if not flavors:
            raise ObjectNotFoundError(
                f"Flavor with name '{flavor_identifier}' not found"
            )
        if len(flavors) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple flavors found with name '{flavor_identifier}'"
            )
        return flavors[0].url


def get_flavor_url_from_params(
    client: AuthenticatedClient, flavor_min_cpu: int, flavor_min_ram: int
):
    """Get flavor URL based on minimum CPU and RAM requirements."""
    flavors = openstack_flavors_list.sync(
        client=client,
        o=[
            OpenstackFlavorsListOItem.CORES,
            OpenstackFlavorsListOItem.RAM,
            OpenstackFlavorsListOItem.DISK,
        ],
        cores_gte=flavor_min_cpu,
        ram_gte=flavor_min_ram,
    )
    if not flavors:
        cpu_msg = f"cores >= {flavor_min_cpu}" if flavor_min_cpu else "any cores"
        ram_msg = f"RAM >= {flavor_min_ram}" if flavor_min_ram else "any RAM"
        raise ObjectNotFoundError(f"No flavor found with {cpu_msg} and {ram_msg}")
    return flavors[0].url


def get_image_url(client: AuthenticatedClient, image_identifier: str) -> str:
    """Get image URL from identifier (name or UUID)."""
    if is_uuid_like(image_identifier):
        image = openstack_images_retrieve.sync(client=client, uuid=image_identifier)
        if image is None:
            raise ObjectNotFoundError(f"Image with UUID '{image_identifier}' not found")
        return image.url
    else:
        images = openstack_images_list.sync(
            client=client,
            name_exact=image_identifier,
        )
        if not images:
            raise ObjectNotFoundError(f"Image with name '{image_identifier}' not found")
        if len(images) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple images found with name '{image_identifier}'"
            )
        return images[0].url


def get_volume_type_url(
    client: AuthenticatedClient, volume_type_identifier: str
) -> str:
    """Get volume type URL from identifier (name or UUID)."""
    if is_uuid_like(volume_type_identifier):
        volume_type = openstack_volume_types_retrieve.sync(
            client=client, uuid=volume_type_identifier
        )
        if volume_type is None:
            raise ObjectNotFoundError(
                f"Volume type with UUID '{volume_type_identifier}' not found"
            )
        return volume_type.url
    else:
        volume_types = openstack_volume_types_list.sync(
            client=client,
            name_exact=volume_type_identifier,
        )
        if not volume_types:
            raise ObjectNotFoundError(
                f"Volume type with name '{volume_type_identifier}' not found"
            )
        if len(volume_types) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple volume types found with name '{volume_type_identifier}'"
            )
        return volume_types[0].url


def get_security_group_url(
    client: AuthenticatedClient, security_group_identifier: str, tenant_uuid: str
):
    """Get security group URL from identifier (name or UUID)."""
    if is_uuid_like(security_group_identifier):
        security_group = openstack_security_groups_retrieve.sync(
            client=client, uuid=security_group_identifier
        )
        if security_group is None:
            raise ObjectNotFoundError(
                f"Security group with UUID '{security_group_identifier}' not found"
            )
        return security_group.url
    else:
        security_groups = openstack_security_groups_list.sync(
            client=client, name_exact=security_group_identifier, tenant_uuid=tenant_uuid
        )
        if not security_groups:
            raise ObjectNotFoundError(
                f"Security group with name '{security_group_identifier}' not found"
            )
        if len(security_groups) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple security groups found with name '{security_group_identifier}'"
            )
        return security_groups[0].url


def get_server_group_url(
    client: AuthenticatedClient, server_group_identifier: str, tenant_uuid: str
):
    """Get server group URL from identifier (name or UUID)."""
    if is_uuid_like(server_group_identifier):
        server_group = openstack_server_groups_retrieve.sync(
            client=client, uuid=server_group_identifier
        )
        if server_group is None:
            raise ObjectNotFoundError(
                f"Server group with UUID '{server_group_identifier}' not found"
            )
        return server_group.url
    else:
        server_groups = openstack_server_groups_list.sync(
            client=client, name_exact=server_group_identifier, tenant_uuid=tenant_uuid
        )
        if not server_groups:
            raise ObjectNotFoundError(
                f"Server group with name '{server_group_identifier}' not found"
            )
        if len(server_groups) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple server groups found with name '{server_group_identifier}'"
            )
        return server_groups[0].url


def get_ssh_key_url(client: AuthenticatedClient, ssh_key_identifier: str):
    """Get SSH key URL from identifier (name or UUID)."""
    if is_uuid_like(ssh_key_identifier):
        ssh_key = keys_retrieve.sync(client=client, uuid=ssh_key_identifier)
        if ssh_key is None:
            raise ObjectNotFoundError(
                f"SSH key with UUID '{ssh_key_identifier}' not found"
            )
        return ssh_key.url
    else:
        ssh_keys = keys_list.sync(client=client, name_exact=ssh_key_identifier)
        if not ssh_keys:
            raise ObjectNotFoundError(
                f"SSH key with name '{ssh_key_identifier}' not found"
            )
        if len(ssh_keys) > 1:
            raise ResourceMultipleFoundError(
                f"Multiple SSH keys found with name '{ssh_key_identifier}'"
            )
        return ssh_keys[0].url


def send_request_to_waldur(client, module):
    name = module.params["name"]
    project = module.params["project"]
    subnet = module.params.get("subnet")
    present = module.params["state"] == "present"
    delete_volumes = module.params.get("delete_volumes")
    release_floating_ips = module.params.get("release_floating_ips")

    instance = None
    has_changed = False
    try:
        resource, instance = get_instance_via_marketplace(client, name, project)
        if not present:
            if instance.state == CoreStates.OK and instance.runtime_state == "ACTIVE":
                openstack_instances_stop.sync_detailed(
                    client=client, uuid=instance.uuid
                )
                if module.params["wait"]:
                    wait_for_instance(
                        client,
                        instance.uuid,
                        module.params["interval"],
                        module.params["timeout"],
                    )
            request = ResourceTerminateRequest(
                attributes={
                    "delete_volumes": delete_volumes,
                    "release_floating_ips": release_floating_ips,
                }
            )
            marketplace_resources_terminate.sync(
                client=client, uuid=resource.uuid, body=request
            )
            has_changed = True
        else:
            actual_groups = [group.name for group in instance.security_groups or []]
            requested_groups = module.params.get("security_groups") or []
            if actual_groups != requested_groups:
                security_group_request = OpenStackInstanceSecurityGroupsUpdateRequest(
                    security_groups=requested_groups
                )
                openstack_instances_update_security_groups.sync_detailed(
                    client=client,
                    uuid=instance.uuid,
                    body=security_group_request,
                )
                if module.params["wait"]:
                    wait_for_instance(
                        client,
                        instance.uuid,
                        module.params["interval"],
                        module.params["timeout"],
                    )
                has_changed = True
            networks = module.params.get("networks")
            # if update is defined using network syntax, extract expected subnets
            if networks:
                subnet = [net["subnet"] for net in networks]
            if subnet:
                if not isinstance(subnet, list):
                    subnet = [subnet]
                instance_subnets = instance.ports
                needed_update_subnets = False

                for s in instance_subnets:
                    if not (s.subnet_name in subnet or s.subnet_uuid in subnet):
                        needed_update_subnets = True
                        break

                if not needed_update_subnets:
                    instance_subnet_names = {s.subnet_name for s in instance_subnets}
                    instance_subnets_ids = {s.subnet_uuid for s in instance_subnets}
                    for s in subnet:
                        if not (
                            s in instance_subnet_names or s in instance_subnets_ids
                        ):
                            needed_update_subnets = True
                            break

                if needed_update_subnets:
                    ports = [
                        OpenStackNestedPortRequest(subnet=subnet_id)
                        for subnet_id in subnet
                    ]
                    ports_request = OpenStackInstancePortsUpdateRequest(ports=ports)
                    openstack_instances_update_ports.sync_detailed(
                        client=client,
                        uuid=instance.uuid,
                        body=ports_request,
                    )
                    if module.params["wait"]:
                        wait_for_instance(
                            client,
                            instance.uuid,
                            module.params["interval"],
                            module.params["timeout"],
                        )
                    has_changed = True
    except ObjectNotFoundError as e:
        if "not found" not in str(e):
            raise
        if present:
            if isinstance(subnet, list):
                subnet = subnet[0]
            networks = module.params.get("networks") or [
                {"subnet": subnet, "floating_ip": module.params.get("floating_ip")}
            ]
            project_obj = get_project(client, project)
            offering: PublicOfferingDetails = get_offering(
                client, module.params["offering"]
            )
            attributes = {
                "name": module.params["name"],
                "description": module.params.get("description", ""),
                "user_data": module.params.get("user_data"),
                "networks": networks,
            }
            if module.params.get("flavor"):
                attributes["flavor"] = get_flavor_url(
                    client, module.params.get("flavor")
                )
            else:
                if module.params.get("flavor_min_cpu") and module.params.get(
                    "flavor_min_ram"
                ):
                    attributes["flavor"] = get_flavor_url_from_params(
                        client,
                        module.params.get("flavor_min_cpu"),
                        module.params.get("flavor_min_ram"),
                    )
                else:
                    raise ValueError(
                        "flavor_min_cpu and flavor_min_ram are required if flavor is not provided"
                    )
            if module.params.get("image"):
                attributes["image"] = get_image_url(client, module.params.get("image"))
            if module.params.get("system_volume_type"):
                attributes["system_volume_type"] = get_volume_type_url(
                    client, module.params.get("system_volume_type")
                )
            if module.params.get("data_volume_type"):
                attributes["data_volume_type"] = get_volume_type_url(
                    client, module.params.get("data_volume_type")
                )
            if module.params.get("server_group"):
                attributes["server_group"] = get_server_group_url(
                    client, module.params.get("server_group"), project_obj.uuid
                )
            if module.params.get("data_volume_size"):
                attributes["data_volume_size"] = (
                    module.params.get("data_volume_size") * 1024
                )
            if module.params.get("security_groups"):
                attributes["security_groups"] = module.params.get("security_groups")
            if module.params.get("ssh_key"):
                attributes["ssh_key"] = get_ssh_key_url(
                    client, module.params.get("ssh_key")
                )
            if module.params.get("system_volume_size"):
                attributes["system_volume_size"] = module.params.get(
                    "system_volume_size"
                )

            order: OrderCreate = marketplace_orders_create.sync(
                client=client,
                body=OrderCreateRequest(
                    project=project_obj.url,
                    offering=offering.url,
                    accepting_terms_of_service=True,
                    attributes=attributes,
                ),
            )
            marketplace_orders_approve_by_consumer.sync_detailed(
                client=client, uuid=order.uuid
            )
            has_changed = True

            if module.params["wait"]:
                # Wait for instance to be created and get it
                _, instance = get_instance_via_marketplace(client, name, project)
                if instance:
                    wait_for_instance(
                        client,
                        instance.uuid,
                        module.params["interval"],
                        module.params["timeout"],
                    )
    return instance, has_changed


def main():
    module = AnsibleModule(
        argument_spec=get_argument_spec(
            data_volume_size=dict(type="int", default=None),
            delete_volumes=dict(type="bool", default=True),
            flavor_min_cpu=dict(type="int", default=None),
            flavor_min_ram=dict(type="int", default=None),
            flavor=dict(type="str", default=None),
            floating_ip=dict(type="str", default=None),
            image=dict(type="str", default=None),
            networks=dict(type="list", default=None),
            project=dict(type="str", default=None),
            offering=dict(type="str", default=None),
            release_floating_ips=dict(type="bool", default=True),
            security_groups=dict(type="list", default=None),
            server_group=dict(type="str", default=None),
            ssh_key=dict(type="str", default=None),
            subnet=dict(type="list", default=None),
            system_volume_size=dict(type="int", default=None),
            user_data=dict(type="str", default=None),
            system_volume_type=dict(type="str", default=None),
            data_volume_type=dict(type="str", default=None),
        ),
        mutually_exclusive=[
            ["subnet", "networks"],
            ["floating_ip", "networks"],
            ["flavor_min_cpu", "flavor"],
            ["flavor_min_ram", "flavor"],
        ],
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    project = module.params["project"]
    offering = module.params["offering"]
    image = module.params["image"]
    flavor = module.params["flavor"]
    flavor_min_cpu = module.params["flavor_min_cpu"]
    flavor_min_ram = module.params["flavor_min_ram"]
    subnet = module.params["subnet"]
    networks = module.params["networks"]
    system_volume_size = module.params["system_volume_size"]

    instance_exists = True
    client = get_client(module)
    project, os_instance = get_instance_via_marketplace(client, name, project)
    if not os_instance:
        instance_exists = False

    if state == "present" and not instance_exists:
        if not project:
            module.fail_json(
                msg="Parameter 'project' is required if state == 'present'"
            )
        if not offering:
            module.fail_json(
                msg="Parameter 'offering' is required if state == 'present'"
            )
        if not image:
            module.fail_json(msg="Parameter 'image' is required if state == 'present'")
        if not (flavor or (flavor_min_cpu and flavor_min_ram)):
            module.fail_json(
                msg="Parameter 'flavor' or ('flavor_min_cpu' and 'flavor_min_ram')"
                " is required if state == 'present'"
            )
        if not system_volume_size:
            module.fail_json(
                msg="Parameter 'system_volume_size' is required if state == 'present'"
            )
        if not networks and not subnet:
            module.fail_json(
                msg="Parameter 'networks' or 'subnet' is required if state == 'present'"
            )
    try:
        instance, has_changed = send_request_to_waldur(client, module)
    except (
        UnexpectedStatus,
        ObjectNotFoundError,
        ObjectStateError,
        ResourceMultipleFoundError,
    ) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(instance=instance, changed=has_changed)


if __name__ == "__main__":
    main()
