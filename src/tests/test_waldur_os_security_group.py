import unittest
from unittest import mock
import respx
import uuid

from ansible_waldur_module import waldur_os_security_group
from ansible_waldur_module.utils import get_client
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models

WEB = {
    "url": "api/123",
    "description": "descr",
    "rules": [
        {
            "from_port": "80",
            "to_port": "80",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
            "remote_group": None,
        }
    ],
}

SSH = {
    "url": "api/124",
    "description": "descr",
    "rules": [
        {
            "from_port": "80",
            "to_port": "80",
            "remote_group": "api/123",
            "protocol": "tcp",
            "direction": "ingress",
            "cidr": None,
            "ethertype": "IPv4",
        }
    ],
}


def fail_side_effect(*args, **kwargs):
    raise Exception(kwargs["msg"])


BASE_URL = "https://waldur.example.com"


def mock_tenant_lookup(tenant_dict, tenant_name="tenant"):
    """Mock tenant lookup by name"""
    respx.get(
        f"{BASE_URL}/api/openstack-tenants/",
        params={"name_exact": tenant_name},
    ).respond(200, json=[tenant_dict])


def mock_tenant_lookup_by_resource(resource_dict):
    """Mock tenant lookup by resource UUID (no name_exact param)"""
    respx.get(
        f"{BASE_URL}/api/marketplace-resources/{resource_dict['uuid']}/",
    ).respond(200, json=resource_dict)


def mock_security_group_lookup(tenant_uuid, group_name, security_groups=None):
    """Mock security group lookup"""
    if security_groups is None:
        security_groups = []
    respx.get(
        f"{BASE_URL}/api/openstack-security-groups/",
        params={"tenant_uuid": tenant_uuid, "name_exact": group_name},
    ).respond(200, json=security_groups)


def mock_security_group_creation(tenant_uuid, response_dict):
    """Mock security group creation"""
    return respx.post(
        f"{BASE_URL}/api/openstack-tenants/{tenant_uuid}/create_security_group/",
    ).respond(201, json=response_dict)


def create_mock_security_group(name, description="descr", rules=None):
    """Create a mock security group instance"""
    if rules is None:
        rules = []
    security_group = generate_example_instance(models.OpenStackSecurityGroup)
    security_group.uuid = str(uuid.uuid4())
    security_group.name = name
    security_group.description = description
    security_group.rules = rules
    return serialize_attrs_instance(security_group)


class SecurityGroupCreateTest(unittest.TestCase):
    def setUp(self) -> None:
        respx.start()

        tenant = generate_example_instance(models.OpenStackTenant)
        tenant.uuid = str(uuid.uuid4())
        tenant.name = "tenant"
        self.tenant_dict = serialize_attrs_instance(tenant)

        self.security_group_dict = create_mock_security_group("sec-group")

        self.create_sg_call_kwargs = dict(
            project=None,
            tenant="tenant",
            name="sec-group",
            description="descr",
            rules=[],
            tags=None,
            wait=True,
            interval=20,
            timeout=600,
        )

        module = mock.Mock()
        module.params = {
            "access_token": "token",
            "api_url": BASE_URL,
            "tenant": "tenant",
            "description": "descr",
            "state": "present",
            "name": "sec-group",
            "wait": False,
            "interval": 20,
            "timeout": 600,
        }
        module.check_mode = False
        self.module = module
        self.client = get_client(module)

    def tearDown(self) -> None:
        respx.stop()

    def check_successful_function_call(self):
        has_changed = waldur_os_security_group.send_request_to_waldur(
            self.client, self.module
        )

        self.assertTrue(has_changed)

    def check_unsuccessful_function_call(self, msg):
        self.module.fail_json.side_effect = fail_side_effect

        self.assertRaisesRegex(
            Exception,
            msg,
            waldur_os_security_group.send_request_to_waldur,
            self.client,
            self.module,
        )

    def test_group_creation_with_link_to_remote_group(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "remote_group": "web",
                "protocol": "tcp",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)

        remote_sg = create_mock_security_group("web")
        remote_sg["url"] = "api/123"
        mock_security_group_lookup(self.tenant_dict["uuid"], "web", [remote_sg])

        mock_security_group_lookup(self.tenant_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            self.tenant_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_if_marketplace_resource_uuid_has_been_passed(self):
        tenant_with_resource = generate_example_instance(models.OpenStackTenant)
        tenant_with_resource.uuid = str(uuid.uuid4())
        resource_uuid = uuid.uuid4().hex
        tenant_with_resource.marketplace_resource_uuid = resource_uuid
        tenant_with_resource_dict = serialize_attrs_instance(tenant_with_resource)

        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "remote_group": "web",
                "protocol": "tcp",
            }
        ]

        self.module.params.pop("tenant")
        self.module.params["waldur_resource"] = resource_uuid
        waldur_resource = generate_example_instance(models.Resource)
        waldur_resource.uuid = resource_uuid
        waldur_resource.scope = (
            f"{BASE_URL}/api/openstack-tenants/{tenant_with_resource_dict['uuid']}/"
        )
        waldur_resource_dict = serialize_attrs_instance(waldur_resource)
        mock_tenant_lookup_by_resource(waldur_resource_dict)
        remote_sg = create_mock_security_group("web")
        remote_sg["url"] = "api/123"
        mock_security_group_lookup(
            tenant_with_resource_dict["uuid"], "web", [remote_sg]
        )

        mock_security_group_lookup(tenant_with_resource_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            tenant_with_resource_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_group_creation_erred_with_invalid_params(self):
        self.module.params["rules"] = [
            {"from_port": "80", "to_port": "80", "protocol": "tcp"}
        ]
        self.module.fail_json.side_effect = fail_side_effect

        mock_tenant_lookup(self.tenant_dict)

        self.check_unsuccessful_function_call(
            "Either cidr or remote_group must be specified."
        )

    def test_group_creation_with_valid_ipv4_cidr(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)
        mock_security_group_lookup(self.tenant_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            self.tenant_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_group_creation_with_valid_ipv6_cidr(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "2002::/16",
                "protocol": "tcp",
                "ethertype": "IPv6",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)
        mock_security_group_lookup(self.tenant_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            self.tenant_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_group_creation_with_invalid_v6_address(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "ethertype": "IPv6",
            }
        ]
        mock_tenant_lookup(self.tenant_dict)
        self.check_unsuccessful_function_call("Invalid IPv6 address")

    def test_group_creation_with_invalid_v4_address(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "2002::/16",
                "protocol": "tcp",
                "ethertype": "IPv4",
            }
        ]
        mock_tenant_lookup(self.tenant_dict)
        self.check_unsuccessful_function_call("Invalid IPv4 address")

    def test_group_creation_with_invalid_ethertype(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "2002::/16",
                "protocol": "tcp",
                "ethertype": "ABC",
            }
        ]
        mock_tenant_lookup(self.tenant_dict)
        self.check_unsuccessful_function_call("Invalid ethertype")

    def test_group_creation_with_ingress_direction(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "direction": "ingress",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)
        mock_security_group_lookup(self.tenant_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            self.tenant_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_group_creation_with_egress_direction(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "direction": "egress",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)
        mock_security_group_lookup(self.tenant_dict["uuid"], "sec-group", [])

        create_request = mock_security_group_creation(
            self.tenant_dict["uuid"], self.security_group_dict
        )

        self.check_successful_function_call()
        self.assertEqual(1, create_request.call_count)

    def test_group_creation_with_invalid_direction(self):
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "direction": "invalid",
            }
        ]
        mock_tenant_lookup(self.tenant_dict)
        self.check_unsuccessful_function_call(
            "Invalid direction invalid expected ingress or egress"
        )

    def test_group_creation_if_group_already_exists(self):
        self.module.params["name"] = "ssh"
        self.module.params["rules"] = [
            {
                "from_port": "80",
                "to_port": "80",
                "remote_group": "web",
                "protocol": "tcp",
                "direction": "ingress",
            }
        ]

        mock_tenant_lookup(self.tenant_dict)

        remote_sg = create_mock_security_group("web")
        remote_sg["url"] = "api/123"
        mock_security_group_lookup(self.tenant_dict["uuid"], "web", [remote_sg])

        existing_sg = create_mock_security_group("ssh", "descr", SSH["rules"])
        mock_security_group_lookup(self.tenant_dict["uuid"], "ssh", [existing_sg])

        has_changed = waldur_os_security_group.send_request_to_waldur(
            self.client, self.module
        )

        self.assertFalse(has_changed)

    def test_security_group_rules_comparison_with_cidr_positive(self):
        local_rules = [
            {
                "from_port": "80",
                "to_port": "80",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "direction": "ingress",
                "ethertype": "IPv4",
            }
        ]

        remote_rules = WEB["rules"]

        self.assertTrue(
            waldur_os_security_group.compare_rules(local_rules, remote_rules)
        )

    def test_security_group_rules_with_remote_link_comparison_positive(self):
        local_rules = [
            {
                "from_port": "80",
                "to_port": "80",
                "remote_group": "api/123",
                "protocol": "tcp",
                "direction": "ingress",
                "ethertype": "IPv4",
            }
        ]

        remote_rules = SSH["rules"]

        self.assertFalse(
            waldur_os_security_group.compare_rules(local_rules, remote_rules)
        )

    def test_security_group_rules_comparison_with_cidr_negative(self):
        local_rules = [
            {
                "from_port": "81",
                "to_port": "81",
                "cidr": "192.168.0.0/28",
                "protocol": "tcp",
                "direction": "ingress",
                "ethertype": "IPv4",
            }
        ]

        remote_rules = WEB["rules"]

        self.assertFalse(
            waldur_os_security_group.compare_rules(local_rules, remote_rules)
        )

    def test_security_group_rules_with_remote_link_comparison_negative(self):
        local_rules = [
            {
                "from_port": "80",
                "to_port": "80",
                "remote_group": "api/124",
                "protocol": "tcp",
                "direction": "ingress",
                "ethertype": "IPv4",
            }
        ]

        remote_rules = SSH["rules"]

        self.assertFalse(
            waldur_os_security_group.compare_rules(local_rules, remote_rules)
        )


class CompareRulesFunctionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules_1 = {
            "from_port": "80",
            "to_port": "80",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
        }
        self.rules_2 = {
            "from_port": "100",
            "to_port": "100",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
        }

    def test_compare_rules(self):
        self.assertTrue(
            waldur_os_security_group.compare_rules([self.rules_1], [self.rules_1])
        )

        self.assertFalse(
            waldur_os_security_group.compare_rules([self.rules_1], [self.rules_2])
        )

        self.assertTrue(
            waldur_os_security_group.compare_rules(
                [self.rules_1, self.rules_2], [self.rules_1, self.rules_2]
            )
        )

        self.assertTrue(
            waldur_os_security_group.compare_rules(
                [self.rules_1, self.rules_2], [self.rules_2, self.rules_1]
            )
        )

    def test_compare_rules_if_remote_group_passed(self):
        local_1 = {
            "from_port": "100",
            "to_port": "100",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
        }
        remote_1 = {
            "from_port": "100",
            "to_port": "100",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
            "remote_group": "api/124",
        }

        self.assertTrue(waldur_os_security_group.compare_rules([local_1], [remote_1]))

        local_2 = {
            "from_port": "80",
            "to_port": "80",
            "protocol": "tcp",
            "direction": "ingress",
            "remote_group": "api/124",
        }
        remote_2 = {
            "from_port": "80",
            "to_port": "80",
            "cidr": "192.168.0.0/28",
            "protocol": "tcp",
            "direction": "ingress",
            "ethertype": "IPv4",
            "remote_group": "api/124",
        }

        self.assertTrue(waldur_os_security_group.compare_rules([local_2], [remote_2]))
        self.assertTrue(
            waldur_os_security_group.compare_rules(
                [local_1, local_2], [remote_2, remote_1]
            )
        )

        remote_2.pop("remote_group")
        self.assertFalse(waldur_os_security_group.compare_rules([local_2], [remote_2]))


class CompareDescriptionFunctionTest(unittest.TestCase):
    def test_compare_description(self):
        self.assertTrue(
            waldur_os_security_group.compare_description("description", "description")
        )

        self.assertFalse(
            waldur_os_security_group.compare_description(
                "description", "new description"
            )
        )

        self.assertTrue(waldur_os_security_group.compare_description("", "  "))

        self.assertTrue(waldur_os_security_group.compare_description("", None))
