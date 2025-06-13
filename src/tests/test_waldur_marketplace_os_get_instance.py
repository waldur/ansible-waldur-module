import unittest
from unittest import mock
import respx
from ansible_waldur_module import waldur_marketplace_os_get_instance
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models


@mock.patch("ansible_waldur_module.waldur_marketplace_os_get_instance.AnsibleModule")
class TestWaldurMarketplaceOsGetInstance(unittest.TestCase):
    TEST_INSTANCE_NAME = "test-instance"
    TEST_PROJECT_NAME = "test-project"

    def setUp(self):
        respx.start()

        # Generate test instances using factory
        project = generate_example_instance(models.Project)
        project.name = self.TEST_PROJECT_NAME
        self.project_dict = serialize_attrs_instance(project)

        instance = generate_example_instance(models.OpenStackInstance)
        instance.name = self.TEST_INSTANCE_NAME
        self.instance_dict = serialize_attrs_instance(instance)

        # Create module mock with proper params dictionary
        self.module = mock.Mock()
        self.module.params = {
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
        }

    def tearDown(self):
        respx.stop()

    def test_instance_found(self, mock_module):
        """
        Test that the module returns the instance when it is found
        """
        mock_module.return_value = self.module

        respx.get(
            "http://example.com:8000/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).respond(status_code=200, json=[self.project_dict])

        respx.get(
            "http://example.com:8000/api/openstack-instances/",
            params={
                "name": self.TEST_INSTANCE_NAME,
                "project": self.project_dict["uuid"],
            },
        ).respond(status_code=200, json=[self.instance_dict])

        waldur_marketplace_os_get_instance.main()
        self.module.exit_json.assert_called_once_with(instance=self.instance_dict)

    def test_instance_not_found(self, mock_module):
        """
        Test that the module fails when the instance return is empty
        """
        mock_module.return_value = self.module

        respx.get(
            "http://example.com:8000/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).respond(status_code=200, json=[self.project_dict])

        respx.get(
            "http://example.com:8000/api/openstack-instances/",
            params={
                "name": self.TEST_INSTANCE_NAME,
                "project": self.project_dict["uuid"],
            },
        ).respond(status_code=200, json=[])

        waldur_marketplace_os_get_instance.main()
        self.module.fail_json.assert_called_once_with(msg="list index out of range")
        self.module.exit_json.assert_not_called()

    def test_project_not_found(self, mock_module):
        """
        Test that the module fails when the project is not found
        """
        mock_module.return_value = self.module

        respx.get(
            "http://example.com:8000/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).respond(status_code=200, json=[])

        waldur_marketplace_os_get_instance.main()
        self.module.fail_json.assert_called_with(
            msg=f"Project '{self.TEST_PROJECT_NAME}' not found"
        )
