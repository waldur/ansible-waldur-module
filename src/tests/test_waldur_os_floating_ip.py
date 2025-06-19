import unittest
from unittest import mock
import respx

from ansible_waldur_module import waldur_os_floating_ip
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models
import json
from waldur_api_client.models.core_states import CoreStates


@mock.patch("ansible_waldur_module.waldur_os_floating_ip.AnsibleModule")
class TestWaldurOsFloatingIp(unittest.TestCase):
    TEST_INSTANCE_NAME = "test-vm-instance"
    TEST_SUBNET = "test-subnet"
    TEST_ADDRESS = "10.30.201.18"
    API_URL = "http://example.com:8000"

    def setUp(self):
        respx.start()

        instance = generate_example_instance(models.OpenStackInstance)
        instance.name = self.TEST_INSTANCE_NAME
        self.instance_dict = serialize_attrs_instance(instance)

        self.module = mock.Mock()
        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "instance": self.TEST_INSTANCE_NAME,
            "state": "present",
            "wait": False,
        }
        self.module.check_mode = False

    def tearDown(self):
        respx.stop()

    def mock_instance_lookup(self, instance_dict=None, empty=False):
        if instance_dict is None:
            instance_dict = self.instance_dict
        return respx.get(
            f"{self.API_URL}/api/openstack-instances/",
            params={"name": self.TEST_INSTANCE_NAME},
        ).respond(json=[] if empty else [instance_dict])

    def mock_instance_lookup_by_uuid(self, instance_dict=None):
        if instance_dict is None:
            instance_dict = self.instance_dict
        return respx.get(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/",
        ).respond(json=instance_dict)

    def mock_update_floating_ips(self):
        return respx.post(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/update_floating_ips/",
        ).respond(status_code=200, json={"status": "ok"})

    def test_assign_single_floating_ip(self, mock_module):
        mock_module.return_value = self.module
        self.module.params.update(
            {
                "address": self.TEST_ADDRESS,
                "subnet": self.TEST_SUBNET,
            }
        )

        self.mock_instance_lookup()
        self.mock_update_floating_ips()

        waldur_os_floating_ip.main()
        self.module.exit_json.assert_called_once()
        self.module.fail_json.assert_not_called()

    def test_assign_multiple_floating_ips(self, mock_module):
        mock_module.return_value = self.module
        self.module.params.update(
            {
                "floating_ips": [
                    {"address": "10.0.0.1", "subnet": "subnet-1"},
                    {"address": "10.0.0.2", "subnet": "subnet-2"},
                ]
            }
        )

        self.mock_instance_lookup()
        request = self.mock_update_floating_ips()
        expected_body = {
            "floating_ips": [{"subnet": "subnet-1"}, {"subnet": "subnet-2"}]
        }

        waldur_os_floating_ip.main()
        self.module.exit_json.assert_called_once()
        self.module.fail_json.assert_not_called()
        self.assertEqual(json.loads(request.calls[0].request._content), expected_body)

    def test_detach_floating_ips(self, mock_module):
        mock_module.return_value = self.module
        self.module.params["state"] = "absent"

        self.mock_instance_lookup()
        request = self.mock_update_floating_ips()
        expected_body = {"floating_ips": []}

        waldur_os_floating_ip.main()
        self.module.exit_json.assert_called_once()
        self.module.fail_json.assert_not_called()
        self.assertEqual(json.loads(request.calls[0].request._content), expected_body)

    def test_instance_not_found(self, mock_module):
        mock_module.return_value = self.module
        self.module.params.update(
            {
                "address": self.TEST_ADDRESS,
                "subnet": self.TEST_SUBNET,
            }
        )

        self.mock_instance_lookup(empty=True)
        with self.assertRaises(IndexError):
            waldur_os_floating_ip.main()
        self.module.fail_json.assert_called_once_with(
            msg=f"Instance with name '{self.TEST_INSTANCE_NAME}' not found"
        )

    def test_wait_for_instance(self, mock_module):
        mock_module.return_value = self.module
        self.instance_dict["state"] = CoreStates.OK
        self.module.params.update(
            {
                "address": self.TEST_ADDRESS,
                "subnet": self.TEST_SUBNET,
                "wait": True,
                "timeout": 10,
                "interval": 5,
            }
        )

        self.mock_instance_lookup()
        self.mock_update_floating_ips()
        self.mock_instance_lookup_by_uuid()

        waldur_os_floating_ip.main()
        self.module.exit_json.assert_called_once()

    def test_wait_failed_instance(self, mock_module):
        mock_module.return_value = self.module
        self.instance_dict["state"] = CoreStates.ERRED
        self.module.params.update(
            {
                "address": self.TEST_ADDRESS,
                "subnet": self.TEST_SUBNET,
                "wait": True,
                "timeout": 10,
                "interval": 5,
            }
        )

        self.mock_instance_lookup()
        self.mock_update_floating_ips()
        self.mock_instance_lookup_by_uuid()

        waldur_os_floating_ip.main()
        self.module.fail_json.assert_called_once()
        self.assertIn(
            "Instance is in erred state", self.module.fail_json.call_args[1]["msg"]
        )

    def test_wait_timeout_instance(self, mock_module):
        mock_module.return_value = self.module
        self.instance_dict["state"] = CoreStates.UPDATING
        self.module.params.update(
            {
                "address": self.TEST_ADDRESS,
                "subnet": self.TEST_SUBNET,
                "wait": True,
                "timeout": 3,
                "interval": 1,
            }
        )

        self.mock_instance_lookup()
        self.mock_update_floating_ips()
        self.mock_instance_lookup_by_uuid()

        waldur_os_floating_ip.main()
        self.module.fail_json.assert_called_once()
        self.assertIn(
            " has not reached stable state", self.module.fail_json.call_args[1]["msg"]
        )
