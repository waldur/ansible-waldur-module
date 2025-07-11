import unittest
from unittest import mock
import respx

from ansible_waldur_module import waldur_marketplace_os_volume
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models
from ansible_waldur_module.utils import get_client
import uuid


@mock.patch("ansible_waldur_module.waldur_marketplace_os_volume.AnsibleModule")
class TestWaldurMarketplaceOsVolume(unittest.TestCase):
    def setUp(self):
        respx.start()
        volume_type = generate_example_instance(models.OpenStackVolumeType)
        self.volume_type_dict = serialize_attrs_instance(volume_type)
        order = generate_example_instance(models.OrderCreate)
        self.order_dict = serialize_attrs_instance(order)
        volume = generate_example_instance(models.OpenStackVolume)
        volume.uuid = str(uuid.uuid4())
        self.volume_dict = serialize_attrs_instance(volume)
        offering = generate_example_instance(models.Offering)
        offering.uuid = str(uuid.uuid4())
        self.offering_dict = serialize_attrs_instance(offering)
        project = generate_example_instance(models.Project)
        project.uuid = str(uuid.uuid4())
        order_details = generate_example_instance(models.OrderDetails)
        order_details.uuid = self.order_dict["uuid"]
        self.order_details_dict = serialize_attrs_instance(order_details)
        self.project_dict = serialize_attrs_instance(project)
        self.module = mock.Mock()
        self.volume_name = "Test volume"
        self.module.params = {
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "name": self.volume_name,
            "project": self.project_dict["uuid"],
            "offering": self.offering_dict["uuid"],
            "size": 10,
            "type": "lvm",
            "state": "present",
            "wait": False,
            "timeout": 600,
            "interval": 20,
        }
        self.module.check_mode = False

    def tearDown(self):
        respx.stop()

    def test_create_volume(self, mock_ansible_module):
        respx.get(
            "http://example.com:8000/api/openstack-volumes/",
            params={
                "name_exact": self.volume_name,
                "project_uuid": str(self.project_dict["uuid"]),
            },
        ).respond(
            200,
            json=[],
        )
        respx.get(f"/api/projects/{self.project_dict['uuid']}/").respond(
            200,
            json=self.project_dict,
        )
        respx.get(
            f"/api/marketplace-public-offerings/{self.offering_dict['uuid']}/"
        ).respond(
            200,
            json=self.offering_dict,
        )
        respx.get("/api/openstack-volume-types/").respond(
            200,
            json=[self.volume_type_dict],
        )
        order_request = respx.post("/api/marketplace-orders/").respond(
            201,
            json=self.order_dict,
        )
        respx.get(f"/api/marketplace-orders/{self.order_dict['uuid']}/").respond(
            200,
            json=self.order_details_dict,
        )
        client = get_client(self.module)

        has_changed = waldur_marketplace_os_volume.send_request_to_waldur(
            client, self.module
        )

        self.assertTrue(has_changed)
        self.assertEqual(1, order_request.call_count)

    def test_delete_volume(self, mock_ansible_module):
        self.module.params["state"] = "absent"
        self.volume_dict["marketplace_resource_uuid"] = str(uuid.uuid4())
        respx.get(f"/api/projects/{self.project_dict['uuid']}/").respond(
            200,
            json=self.project_dict,
        )
        respx.get(
            "http://example.com:8000/api/openstack-volumes/",
            params={
                "name_exact": self.volume_name,
                "project_uuid": str(self.project_dict["uuid"]),
            },
        ).respond(
            200,
            json=[self.volume_dict],
        )
        delete_request = respx.post(
            f"/api/marketplace-resources/{self.volume_dict['marketplace_resource_uuid']}/terminate/"
        ).respond(
            200,
            json={"order_uuid": str(uuid.uuid4())},
        )
        client = get_client(self.module)
        has_changed = waldur_marketplace_os_volume.send_request_to_waldur(
            client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(1, delete_request.call_count)
