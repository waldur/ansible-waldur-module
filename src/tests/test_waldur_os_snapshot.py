import unittest
from unittest import mock
import respx
import httpx

from ansible_waldur_module import waldur_os_snapshot
from waldur_api_client.models.open_stack_volume import OpenStackVolume
from waldur_api_client.models.open_stack_snapshot import OpenStackSnapshot
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
from waldur_api_client.models.core_states import CoreStates
from ansible_waldur_module.utils import get_client


@mock.patch("ansible_waldur_module.waldur_os_snapshot.AnsibleModule")
class TestWaldurOsSnapshot(unittest.TestCase):
    def setUp(self):
        self.module = mock.Mock()
        respx.start()
        self.module.params = {
            "name": "Test snapshot",
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "volume": "Test volume",
            "description": "Test description",
            "kept_until": "2025-12-31",
            "state": "present",
            "tags": ["tag1", "tag2"],
            "wait": True,
            "timeout": 10,
            "interval": 5,
        }
        self.module.check_mode = False

    def tearDown(self):
        respx.mock.stop()

    def test_create_snapshot(self, mock_ansible_module):
        volume = generate_example_instance(OpenStackVolume)
        volume.name = self.module.params["volume"]

        respx.get(
            f"{self.module.params['api_url']}/api/openstack-volumes/",
            params={"name": self.module.params["volume"]},
        ).respond(json=[serialize_attrs_instance(volume)])
        snapshot = generate_example_instance(OpenStackSnapshot)
        snapshot.name = self.module.params["name"]
        snapshot.state = CoreStates.CREATION_SCHEDULED
        respx.get(
            f"{self.module.params['api_url']}/api/openstack-snapshots/",
            params={"name": self.module.params["name"]},
        ).respond(json=[])

        snapshot.name = "testtesttest"
        # More explicit mock setup
        mock_response = serialize_attrs_instance(snapshot)

        respx.post(
            f"{self.module.params['api_url']}/api/openstack-volumes/{volume.uuid}/snapshot/",
        ).respond(status_code=201, json=mock_response)

        snapshot.state = CoreStates.OK
        respx.get(
            f"{self.module.params['api_url']}/api/openstack-snapshots/{snapshot.uuid}/"
        ).mock(
            return_value=httpx.Response(
                status_code=200, json=serialize_attrs_instance(snapshot)
            )
        )

        client = get_client(self.module)
        has_changed = waldur_os_snapshot.send_request_to_waldur(client, self.module)
        self.assertTrue(has_changed)
