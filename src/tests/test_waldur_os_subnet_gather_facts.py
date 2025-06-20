import unittest
from unittest import mock
import respx

from ansible_waldur_module import waldur_os_subnet_gather_facts
from waldur_api_client.models.open_stack_sub_net import OpenStackSubNet
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
from ansible_waldur_module.utils import get_client
import uuid


@mock.patch("ansible_waldur_module.waldur_os_subnet_gather_facts.AnsibleModule")
class TestWaldurOsSubnetGatherFacts(unittest.TestCase):
    def setUp(self):
        self.module = mock.Mock()
        respx.start()
        subnet_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        openstack_subnet = generate_example_instance(OpenStackSubNet)
        openstack_subnet.uuid = subnet_uuid
        self.subnet_dict = serialize_attrs_instance(openstack_subnet)
        self.module.params = {
            "name": "Test snapshot",
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "subnet_uuid": subnet_uuid,
            "tenant_uuid": tenant_uuid,
        }
        self.client = get_client(self.module)

    def tearDown(self):
        respx.stop()

    def test_get_subnets_by_subnet_uuid(self, mock_ansible_module):
        mock_ansible_module.return_value = self.module

        respx.get(
            f"/api/openstack-subnets/{self.module.params['subnet_uuid']}/"
        ).respond(
            200,
            json=self.subnet_dict,
        )

        waldur_os_subnet_gather_facts.send_request_to_waldur(self.client, self.module)
        self.module.fail_json.assert_not_called()

    def test_get_subnets_by_tenant_uuid(self, mock_ansible_module):
        mock_ansible_module.return_value = self.module
        self.module.params["subnet_uuid"] = None
        subnet_request = respx.get(
            "/api/openstack-subnets/",
            params={"tenant_uuid": self.module.params["tenant_uuid"]},
        ).respond(
            200,
            json=[self.subnet_dict],
        )

        waldur_os_subnet_gather_facts.send_request_to_waldur(self.client, self.module)
        self.module.fail_json.assert_not_called()
        self.assertEqual(subnet_request.call_count, 1)

    def test_get_subnets_by_invalid_subnet_uuid(self, mock_ansible_module):
        mock_ansible_module.return_value = self.module
        self.module.params["subnet_uuid"] = "invalid-uuid"
        with self.assertRaises(ValueError):
            waldur_os_subnet_gather_facts.send_request_to_waldur(
                self.client, self.module
            )
            self.module.fail_json.assert_called_once()
