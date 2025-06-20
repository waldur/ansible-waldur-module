import unittest
from unittest import mock
import respx
from ansible_waldur_module import waldur_os_subnet
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
from ansible_waldur_module.utils import get_client
from waldur_api_client import models
import uuid
import json


def fail_side_effect(*args, **kwargs):
    raise Exception(kwargs["msg"])


BASE_URL = "https://waldur.example.com"


class BaseSubnetTest(unittest.TestCase):
    def setUp(self):
        respx.start()
        self.module = mock.Mock()
        self.subnet_uuid = str(uuid.uuid4())
        self.module.params = {
            "access_token": "token",
            "api_url": BASE_URL,
            "subnet_uuid": self.subnet_uuid,
            "name": "subnet",
            "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
            "disable_gateway": False,
            "gateway_ip": "192.168.42.1",
            "state": "present",
            "wait": False,
            "interval": 10,
            "timeout": 600,
        }
        self.client = get_client(self.module)
        self.subnet = generate_example_instance(models.OpenStackSubNet)
        self.subnet.uuid = self.subnet_uuid
        self.subnet_dict = serialize_attrs_instance(self.subnet)

    def test_valid_gateway_config(self):
        """
        Test that the gateway IP is updated
        """
        self.subnet_dict["disable_gateway"] = False
        self.subnet_dict["gateway_ip"] = "192.168.42.2"
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        self.subnet_dict["gateway_ip"] = "192.168.42.2"
        respx.put(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)

    def test_name_update(self):
        """
        Test that the name is updated
        """
        self.module.params["name"] = "subnet_test"
        self.subnet_dict["name"] = "subnet_test"
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        update_request = respx.put(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/"
        ).respond(200, json=self.subnet_dict)
        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, update_request.call_count)
        request_data = json.loads(update_request.calls[0].request._content)
        self.assertEqual(self.subnet_dict["name"], request_data["name"])

    def test_create_subnet(self):
        """
        Test that the subnet is created
        """
        network_uuid = str(uuid.uuid4())

        self.module.params = {
            "name": "subnet-creation-net",
            "gateway_ip": "192.168.42.1",
            "disable_gateway": False,
            "cidr": "192.168.42.0/24",
            "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
            "wait": False,
            "interval": 10,
            "timeout": 600,
            "network_uuid": network_uuid,
            "state": "present",
        }
        self.subnet_dict["name"] = self.module.params["name"]
        self.subnet_dict["cidr"] = self.module.params["cidr"]
        self.subnet_dict["gateway_ip"] = self.module.params["gateway_ip"]
        self.subnet_dict["disable_gateway"] = self.module.params["disable_gateway"]
        self.subnet_dict["dns_nameservers"] = self.module.params["dns_nameservers"]
        create_request = respx.post(
            f"{BASE_URL}/api/openstack-networks/{network_uuid}/create_subnet/"
        ).respond(200, json=self.subnet_dict)
        self.module.check_mode = False
        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, create_request.call_count)

        pass

    def test_dns_nameserver_update(self):
        """
        Test that the dns nameservers are updated
        """
        self.module.params["dns_nameservers"] = []
        self.subnet_dict["dns_nameservers"] = []
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        update_request = respx.put(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/"
        ).respond(200, json=self.subnet_dict)
        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, update_request.call_count)

    def test_connect_subnet(self):
        """
        Test that the subnet is connected to a router
        """
        self.module.params["connect_subnet"] = True
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        connect_request = respx.post(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/connect/"
        ).respond(200, json=self.subnet_dict)

        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, connect_request.call_count)

    def test_disconnect_subnet(self):
        """
        Test that the subnet is disconnected from a router
        """
        self.module.params["disconnect_subnet"] = True
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        disconnect_request = respx.post(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/disconnect/"
        ).respond(200, json=self.subnet_dict)

        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, disconnect_request.call_count)

    def test_unlink_subnet(self):
        """
        Test that the subnet is unlinked (deleted from database without backend operations)
        """
        self.module.params["unlink_subnet"] = True
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        unlink_request = respx.post(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/unlink/"
        ).respond(200, json=self.subnet_dict)

        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertTrue(has_changed)
        self.assertEqual(1, unlink_request.call_count)

    def test_no_update_when_fields_match(self):
        """
        Test that no update is performed when all fields match
        """
        self.subnet_dict["name"] = self.module.params["name"]
        self.subnet_dict["gateway_ip"] = self.module.params["gateway_ip"]
        self.subnet_dict["disable_gateway"] = self.module.params["disable_gateway"]
        self.subnet_dict["dns_nameservers"] = self.module.params["dns_nameservers"]
        respx.get(f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/").respond(
            200, json=self.subnet_dict
        )
        # No PUT request should be made since fields match
        update_request = respx.put(
            f"{BASE_URL}/api/openstack-subnets/{self.subnet_uuid}/"
        ).respond(200, json=self.subnet_dict)
        has_changed = waldur_os_subnet.send_request_to_waldur(self.client, self.module)
        self.assertFalse(has_changed)
        self.assertEqual(0, update_request.call_count)
