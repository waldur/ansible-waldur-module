import tempfile
import unittest
from unittest import mock
import httpx
import respx

from ansible_waldur_module import waldur_marketplace
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models
import ansible_waldur_module.utils as utils
from ansible_waldur_module.exceptions import (
    ObjectNotFoundError,
)


@mock.patch("ansible_waldur_module.waldur_marketplace.AnsibleModule")
class OrderItemCreateTest(unittest.TestCase):
    TEST_PROJECT_NAME = "testproject"
    TEST_OFFERING_NAME = "test-offering"
    TEST_PLAN_NAME = "test-plan"
    API_URL = "http://example.com:8000"

    def setUp(self):
        respx.start()
        module = mock.Mock()
        module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "offering": self.TEST_OFFERING_NAME,
            "plan": self.TEST_PLAN_NAME,
            "project": self.TEST_PROJECT_NAME,
        }
        module.check_mode = False
        self.module = module

        project = generate_example_instance(models.Project)
        project.name = self.TEST_PROJECT_NAME
        self.project_dict = serialize_attrs_instance(project)

        offering = generate_example_instance(models.PublicOfferingDetails)
        offering.name = self.TEST_OFFERING_NAME
        self.offering_dict = serialize_attrs_instance(offering)
        order = generate_example_instance(models.OrderCreate)
        self.order_dict = serialize_attrs_instance(order)
        plan = generate_example_instance(models.ProviderPlanDetails)
        plan.name = self.TEST_PLAN_NAME
        self.plan_dict = serialize_attrs_instance(plan)
        self.client = utils.get_client(self.module)

    def tearDown(self):
        respx.stop()

    def mock_project_lookup(self, project_dict=None):
        if project_dict is None:
            project_dict = self.project_dict
        return respx.get(
            f"{self.API_URL}/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[project_dict]))

    def mock_offering_lookup(self, offering_dict=None):
        if offering_dict is None:
            offering_dict = self.offering_dict
        return respx.get(
            f"{self.API_URL}/api/marketplace-public-offerings/",
            params={"name_exact": self.TEST_OFFERING_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[offering_dict]))

    def mock_plan_lookup(self, plan_dict=None):
        if plan_dict is None:
            plan_dict = self.plan_dict
        return respx.get(
            f"{self.API_URL}/api/marketplace-plans/",
            params={"offering_uuid": self.offering_dict["uuid"]},
        ).mock(return_value=httpx.Response(status_code=200, json=[plan_dict]))

    def mock_order_creation(self, order_dict=None):
        if order_dict is None:
            order_dict = self.order_dict
        return respx.post(
            f"{self.API_URL}/api/marketplace-orders/",
        ).mock(return_value=httpx.Response(status_code=201, json=order_dict))

    def test_fail_json_is_called_if_file_is_not_found(self, mock_ansible_module):
        self.mock_project_lookup()
        self.mock_offering_lookup()
        self.mock_plan_lookup()
        self.module.params["attributes"] = "/file/not/found.json"
        mock_ansible_module.return_value = self.module
        waldur_marketplace.main()
        self.module.fail_json.assert_called_once_with(
            msg="Unable to open file: [Errno 2] No such file or directory: '/file/not/found.json'"
        )

    def test_exit_json_is_called_if_file_is_found(self, mock_ansible_module):
        self.mock_project_lookup()
        self.mock_offering_lookup()
        self.mock_plan_lookup()
        self.mock_order_creation()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        tmp_file.write('{"name": "my name"}')
        tmp_file.close()
        self.module.params["attributes"] = tmp_file.name
        self.module.params["limits"] = '{"cpu": 2, "ram": 4096}'
        mock_ansible_module.return_value = self.module
        waldur_marketplace.main()
        self.module.fail_json.assert_not_called()
        self.module.exit_json.assert_called_once()

    def test_create_marketplace_order_with_sdk(self, mock_ansible_module):
        self.module.params.update(
            {
                "project": self.TEST_PROJECT_NAME,
                "offering": self.TEST_OFFERING_NAME,
                "plan": self.TEST_PLAN_NAME,
                "limits": '{"cpu": 4, "ram": 8192, "storage": 100}',
            }
        )

        self.mock_project_lookup()
        self.mock_offering_lookup()
        self.mock_plan_lookup()
        self.mock_order_creation()

        order, has_changed = waldur_marketplace.send_request_to_waldur(
            self.client, self.module
        )
        self.assertEqual(order, self.order_dict)
        self.assertTrue(has_changed)

    def test_project_not_found_with_sdk(self, mock_ansible_module):
        self.module.params.update(
            {
                "project": self.TEST_PROJECT_NAME,
                "offering": self.TEST_OFFERING_NAME,
                "plan": self.TEST_PLAN_NAME,
            }
        )

        respx.get(
            f"{self.API_URL}/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[]))

        with self.assertRaises(ObjectNotFoundError):
            waldur_marketplace.send_request_to_waldur(self.client, self.module)

    def test_offering_not_found_with_sdk(self, mock_ansible_module):
        self.module.params.update(
            {
                "project": self.TEST_PROJECT_NAME,
                "offering": self.TEST_OFFERING_NAME,
                "plan": self.TEST_PLAN_NAME,
            }
        )

        self.mock_project_lookup()
        respx.get(
            f"{self.API_URL}/api/marketplace-public-offerings/",
            params={"name_exact": self.TEST_OFFERING_NAME},
        ).mock(return_value=httpx.Response(status_code=200, json=[]))

        with self.assertRaises(ValueError):
            waldur_marketplace.send_request_to_waldur(self.client, self.module)
