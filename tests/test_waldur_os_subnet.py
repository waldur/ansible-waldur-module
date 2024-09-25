import unittest
from unittest import mock

import waldur_os_subnet


def fail_side_effect(*args, **kwargs):
    raise Exception(kwargs["msg"])


class BaseSubnetTest(unittest.TestCase):
    def setUp(self):
        self.module = mock.Mock()

        self.module.params = {
            "access_token": "token",
            "api_url": "api",
            "uuid": "df3ee5cac5874dffa1aad86bc1919d8d",
            "name": "subnet",
            "tenant": "tenant",
            "project": "Test-project",
            "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
            "disable_gateway": False,
            "gateway_ip": "192.168.42.1",
            "state": "present",
            "wait": True,
            "interval": 10,
            "timeout": 600,
        }
        self.client = mock.Mock()

    # adapted from waldur_os_security_group
    def check_unsuccessful_function_call(self, msg):
        self.module.fail_json.side_effect = fail_side_effect

        self.assertRaisesRegex(
            Exception,
            msg,
            waldur_os_subnet.send_request_to_waldur,
            self.client,
            self.module,
        )

    def test_valid_gateway_config(self):
        client = mock.Mock()
        client.get_subnet_by_uuid.return_value = {
            "uuid": "uuid",
            "disable_gateway": False,
            "gateway_ip": "192.168.42.2",
        }
        has_changed = waldur_os_subnet.send_request_to_waldur(client, self.module)
        self.assertTrue(has_changed)

    def test_name_update(self):
        client = mock.Mock()
        self.module.params["name"] = "subnet_test"
        client.get_subnet_by_uuid.return_value = {
            "uuid": "uuid",
            "name": "subnet_test",
        }
        has_changed = waldur_os_subnet.send_request_to_waldur(client, self.module)
        self.assertTrue(has_changed)

    def test_create_subnet(self):
        client = mock.Mock()
        self.module.params = {
            "name": "subnet-creation-net",
            "project": "8bd6d84651354c298136b821b9b73626",
            "gateway_ip": "192.168.42.1",
            "disable_gateway": False,
            "cidr": "192.168.42.0/24",
            "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
            "wait": True,
            "interval": 10,
            "timeout": 600,
            "network_uuid": "96172a4c5cf240539778f41ddffda145",
            "tenant": "adaa0a33d18845d7b3af388bfea8208c",
        }
        self.module.check_mode = False
        has_changed = waldur_os_subnet.send_request_to_waldur(client, self.module)
        self.assertTrue(has_changed)

        pass

    def test_dns_nameserver_update(self):
        client = mock.Mock()
        self.module.params["dns_nameservers"] = []
        client.get_subnet_by_uuid.return_value = {
            "uuid": "uuid",
            "dns_nameservers": [],
        }
        has_changed = waldur_os_subnet.send_request_to_waldur(client, self.module)
        self.assertTrue(has_changed)
