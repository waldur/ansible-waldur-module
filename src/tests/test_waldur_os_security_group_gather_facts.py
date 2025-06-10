import unittest
from unittest import mock
import httpx
import respx

from ansible_waldur_module import waldur_os_security_group_gather_facts
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models


@mock.patch("ansible_waldur_module.waldur_os_security_group_gather_facts.AnsibleModule")
class TestWaldurOsSecurityGroupGatherFacts(unittest.TestCase):
    TEST_GROUP_NAME = "classic-web"
    TEST_TENANT_NAME = "VPC1"

    def setUp(self):
        respx.start()
        self.module = mock.Mock()
        tenant = generate_example_instance(models.OpenStackTenant)
        tenant.name = self.TEST_TENANT_NAME
        self.tenant_dict = serialize_attrs_instance(tenant)
        security_group = generate_example_instance(models.OpenStackSecurityGroup)
        security_group.name = self.TEST_GROUP_NAME
        self.security_group_dict = serialize_attrs_instance(security_group)
        self.module.params = {
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "name": self.TEST_GROUP_NAME,
            "tenant": self.TEST_TENANT_NAME,
        }
        self.client = waldur_os_security_group_gather_facts.AuthenticatedClient(
            base_url=self.module.params["api_url"],
            token=self.module.params["access_token"],
            prefix="Token",
        )

    def tearDown(self):
        respx.stop()

    def test_security_group_found(self, mock_module):
        respx.get(
            "http://example.com:8000/api/openstack-tenants/",
            params={"name": self.TEST_TENANT_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[self.tenant_dict]))

        respx.get(
            "http://example.com:8000/api/openstack-security-groups/",
            params={"tenant_uuid": self.tenant_dict["uuid"]},
        ).mock(
            return_value=httpx.Response(
                status_code=200, json=[self.security_group_dict]
            )
        )

        security_groups = waldur_os_security_group_gather_facts.send_request_to_waldur(
            self.client, self.module
        )
        self.assertEqual(
            security_groups[0],
            models.OpenStackSecurityGroup.from_dict(self.security_group_dict),
        )

    def test_security_group_not_found(self, mock_module):
        respx.get(
            "http://example.com:8000/api/openstack-tenants/",
            params={"name": self.TEST_TENANT_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[self.tenant_dict]))

        respx.get(
            "http://example.com:8000/api/openstack-security-groups/",
            params={"tenant_uuid": self.tenant_dict["uuid"]},
        ).mock(return_value=httpx.Response(status_code=200, json=[]))
        waldur_os_security_group_gather_facts.send_request_to_waldur(
            self.client, self.module
        )
        self.module.fail_json.assert_called_once_with(
            msg=f"Security group with name '{self.TEST_GROUP_NAME}' not found"
        )
