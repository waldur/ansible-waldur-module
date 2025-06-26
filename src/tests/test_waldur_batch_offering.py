import unittest
from unittest import mock
import respx

from ansible_waldur_module import waldur_batch_offering
from ansible_waldur_module.utils import get_client


@mock.patch("ansible_waldur_module.waldur_batch_offering.AnsibleModule")
class CreateOfferingTest(unittest.TestCase):
    def setUp(self):
        respx.start()
        module = mock.Mock()
        self.offering_uuid = "12345678-1234-5678-1234-567812345678"
        module.params = {
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "name": "Test offering",
            "category": "12345678-1234-5678-1234-567812345678",
            "provider": "87654321-4321-8765-4321-876543210987",
            "plans": [
                {
                    "name": "Test plan",
                    "unit": "month",
                    "prices": {"cpu": 100, "ram": 64},
                }
            ],
            "batch_service": "SLURM",
            "hostname": "localhost",
            "username": "user",
            "port": "8080",
            "gateway": "localhost",
            "default_account": "root",
        }
        module.check_mode = False
        self.module = module

    def tearDown(self):
        respx.stop()

    def test_create_offering(self, mock_ansible_module):
        # Mock the category retrieve endpoint
        respx.get(
            f"{self.module.params['api_url']}/api/marketplace-categories/{self.module.params['category']}/",
            headers={"Authorization": f"Token {self.module.params['access_token']}"},
        ).respond(
            200,
            json={
                "uuid": self.module.params["category"],
                "name": "Test Category",
                "url": f"{self.module.params['api_url']}/api/marketplace-categories/{self.module.params['category']}/",
            },
        )

        # Mock the provider retrieve endpoint
        respx.get(
            f"{self.module.params['api_url']}/api/customers/{self.module.params['provider']}/",
            headers={"Authorization": f"Token {self.module.params['access_token']}"},
        ).respond(
            200,
            json={
                "uuid": self.module.params["provider"],
                "name": "Test Provider",
                "url": f"{self.module.params['api_url']}/api/customers/{self.module.params['provider']}/",
            },
        )

        # Mock the offering creation endpoint
        respx.post(
            f"{self.module.params['api_url']}/api/marketplace-provider-offerings/",
            headers={"Authorization": f"Token {self.module.params['access_token']}"},
        ).respond(
            201,
            json={
                "url": f"{self.module.params['api_url']}/api/marketplace-provider-offerings/{self.offering_uuid}/",
                "uuid": self.offering_uuid,
                "created": "2024-03-20T12:00:00Z",
                "name": self.module.params["name"],
                "slug": "test-offering",
                "endpoints": [],
                "roles": [],
                "customer_uuid": None,
                "customer_name": None,
                "project": None,
                "project_uuid": None,
                "project_name": None,
                "category": f"{self.module.params['api_url']}/api/marketplace-categories/{self.module.params['category']}/",
                "category_uuid": self.module.params["category"],
                "category_title": "Test Category",
                "plugin_options": {},
                "secret_options": {},
                "service_attributes": {},
                "state": "Draft",
                "order_count": 0,
                "screenshots": [],
                "type": "SlurmInvoices.SlurmPackage",
                "scope": "customer",
                "scope_uuid": None,
                "scope_name": None,
                "scope_state": None,
                "scope_error_message": None,
                "files": [],
                "quotas": [],
                "paused_reason": "",
                "citation_count": 0,
                "organization_groups": [],
                "total_customers": None,
                "total_cost": None,
                "total_cost_estimated": None,
                "parent_description": None,
                "parent_uuid": None,
                "parent_name": None,
            },
        )

        client = get_client(self.module)

        offering, has_changed = waldur_batch_offering.send_request_to_waldur(
            client, self.module
        )

        self.assertTrue(has_changed)
        self.assertEqual(offering["uuid"], self.offering_uuid)
        self.assertEqual(offering["name"], self.module.params["name"])
