#!/usr/bin/python
# has to be a full import due to Ansible 2.0 compatibility
from ansible.module_utils.basic import AnsibleModule
from ansible_waldur_module.exceptions import (
    ResourceError,
    ObjectStateError,
)
from waldur_api_client.api.openstack_volumes import openstack_volumes_list
from waldur_api_client.api.openstack_volumes import openstack_volumes_snapshot
from waldur_api_client.api.openstack_snapshots import openstack_snapshots_list
from waldur_api_client.api.openstack_snapshots import openstack_snapshots_retrieve
from waldur_api_client.api.openstack_snapshots import openstack_snapshots_destroy
from waldur_api_client.models.open_stack_snapshot_request import (
    OpenStackSnapshotRequest,
)
from waldur_api_client.errors import UnexpectedStatus
from ansible_waldur_module.utils import waldur_resource_argument_spec, get_client
import time
from waldur_api_client.models.core_states import CoreStates

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "OpenNode",
}

DOCUMENTATION = """
---
module: waldur_os_snapshot
short_description: Create/Delete OpenStack snapshot
version_added: 0.8
description:
  - "Create/Delete OpenStack snapshot"
requirements:
  - "python = 3.8"
  - "requests"
  - "python-waldur-client"
options:
  access_token:
    description:
      - An access token which has permissions to create a snapshot.
    required: true
  api_url:
    description:
      - Fully qualified URL to the Waldur.
    required: true
  description:
    description:
      - A description of the snapshot.
  interval:
    default: 20
    description:
      - An interval of the snapshot state polling.
  kept_until:
    description:
      - Guaranteed time of snapshot retention. If null - keep forever.
  name:
    description:
      - The name of the snapshot.
    required: true
  state:
    choices:
      - present
      - absent
    default: present
    description:
      - Should the resource be present or absent.
  tags:
    description:
      - List of tags that will be added to the snapshot on provisioning.
  timeout:
    default: 600
    description:
      - The maximum amount of seconds to wait until the snapshot provisioning is finished.
  volume:
    description:
      - The name or id of the OpenStack volume.
        It is required if is state is 'present'.
  wait:
    default: true
    description:
      - A boolean value that defines whether client has to wait until the snapshot is provisioned.
"""

EXAMPLES = """
- name: create snapshot
  hosts: localhost
  tasks:
    - name: create snapshot
      waldur_os_snapshot:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        volume: test volume
        name: test snapshot
        state: present
        kept_until: 2018-12-31

- name: remove snapshot
  hosts: localhost
  tasks:
    - name: remove existing snapshot
      waldur_os_snapshot:
        access_token: b83557fd8e2066e98f27dee8f3b3433cdc4183ce
        api_url: https://waldur.example.com:8000/api
        name: test snapshot
        volume: test volume
        state: absent
"""


def get_volume_by_name(client, volume_name, module):
    volumes = openstack_volumes_list.sync(
        client=client,
        name=volume_name,
    )
    if not volumes:
        module.fail_json(msg=f"Volume with name '{volume_name}' not found")
    return volumes[0]


def get_snapshot_by_name(client, snapshot_name, module):
    snapshots = openstack_snapshots_list.sync(
        client=client,
        name=snapshot_name,
    )
    if not snapshots:
        return None
    return snapshots[0]


def wait_for_snapshot(client, snapshot_uuid, interval=20, timeout=600):
    waited = 0
    while waited < timeout:
        snapshot = openstack_snapshots_retrieve.sync(client=client, uuid=snapshot_uuid)

        if snapshot.state == CoreStates.ERRED:
            raise ObjectStateError(
                f"Snapshot is in erred state: {snapshot.error_message}"
            )

        if snapshot.state == CoreStates.OK:
            return True
        time.sleep(interval)
        waited += interval

    raise ObjectStateError(f'Snapshot "{snapshot_uuid}" has not reached stable state.')


def send_request_to_waldur(client, module):
    has_changed = False
    name = module.params["name"]
    snapshot = get_snapshot_by_name(client, name, module)
    present = module.params["state"] == "present"
    if snapshot and not present:
        openstack_snapshots_destroy.sync_detailed(
            client=client,
            uuid=snapshot.uuid,
        )
        has_changed = True
    elif present:
        wait = module.params["wait"]
        timeout = module.params["timeout"]
        interval = module.params["interval"]
        request = OpenStackSnapshotRequest(
            name=module.params["name"],
            description=module.params.get("description"),
            kept_until=module.params.get("kept_until"),
            metadata=module.params.get("tags"),
        )
        volume = get_volume_by_name(client, module.params["volume"], module)
        snapshot = openstack_volumes_snapshot.sync(
            client=client,
            uuid=volume.uuid,
            body=request,
        )
        if wait:
            wait_for_snapshot(
                client=client,
                snapshot_uuid=snapshot.uuid,
                interval=interval,
                timeout=timeout,
            )
        has_changed = True

    return has_changed


def main():
    fields = waldur_resource_argument_spec(
        kept_until=dict(type="str", default=None),
        volume=dict(type="str", default=None),
    )
    module = AnsibleModule(argument_spec=fields)

    state = module.params["state"]
    volume = module.params["volume"]

    if state == "present":
        if not volume:
            module.fail_json(msg="Parameter 'volume' is required if state == 'present'")

    client = get_client(module)

    try:
        has_changed = send_request_to_waldur(client, module)
    except (UnexpectedStatus, ResourceError, TimeoutError) as e:
        module.fail_json(msg=str(e))
    else:
        module.exit_json(changed=has_changed)


if __name__ == "__main__":
    main()
