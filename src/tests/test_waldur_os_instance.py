import unittest
import uuid
from unittest import mock

import httpx
import respx
import waldur_api_client.models as models

from ansible_waldur_module import waldur_marketplace_os_instance
from tests.utils.factory import generate_example_instance, serialize_attrs_instance


class InstanceSubNetUpdateTest(unittest.TestCase):
    TEST_INSTANCE_NAME = "Test instance"
    TEST_PROJECT_NAME = "Test project"
    TEST_OFFERING_NAME = "test-offering"
    API_URL = "http://example.com:8000"

    def setUp(self):
        respx.start()
        self.module = mock.Mock()
        self.subnets_set = ["subnet_1", "subnet_2"]

        project = generate_example_instance(models.Project)
        project.name = self.TEST_PROJECT_NAME
        self.project_dict = serialize_attrs_instance(project)

        instance = generate_example_instance(models.OpenStackInstance)
        instance.name = self.TEST_INSTANCE_NAME
        instance.state = models.CoreStates.OK
        instance.runtime_state = "ACTIVE"
        self.instance_dict = serialize_attrs_instance(instance)

        resource = generate_example_instance(models.Resource)
        resource.name = self.TEST_INSTANCE_NAME
        self.resource_dict = serialize_attrs_instance(resource)

        offering = generate_example_instance(models.PublicOfferingDetails)
        offering.name = self.TEST_OFFERING_NAME
        self.offering_dict = serialize_attrs_instance(offering)

        order = generate_example_instance(models.OrderCreate)
        self.order_dict = serialize_attrs_instance(order)
        self.order_dict["uuid"] = "08b64cfd-a6d7-4646-8978-932248a9459b"

        order_uuid = generate_example_instance(models.OrderUUID)
        order_uuid.order_uuid = self.order_dict["uuid"]
        self.order_uuid_dict = serialize_attrs_instance(order_uuid)

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "offering": self.TEST_OFFERING_NAME,
            "state": "present",
            "wait": True,
            "interval": 5,
            "timeout": 10,
        }
        self.module.check_mode = False

        self.client = waldur_marketplace_os_instance.AuthenticatedClient(
            base_url=self.module.params["api_url"],
            token=self.module.params["access_token"],
        )
        self.flavor_dict = {
            "url": "http://example.com:8000/api/openstack-flavors/1/",
            "uuid": uuid.uuid4().hex,
            "name": "test-flavor",
            "settings": "{}",
            "cores": 2,
        }
        image = generate_example_instance(models.OpenStackImage)
        image.name = "test-image"
        self.image_dict = serialize_attrs_instance(image)

    def tearDown(self):
        respx.stop()

    def mock_project_lookup(self):
        respx.get(
            f"{self.API_URL}/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).respond(200, json=[self.project_dict])

    def mock_resource_lookup(self):
        respx.get(
            f"{self.API_URL}/api/marketplace-resources/",
            params={
                "project_uuid": self.project_dict["uuid"],
                "name_exact": self.TEST_INSTANCE_NAME,
                "offering_type": "OpenStackTenant.Instance",
            },
        ).respond(200, json=[self.resource_dict])

    def mock_instance_lookup(self):
        respx.get(
            f"{self.API_URL}/api/openstack-instances/",
            params={
                "project_uuid": self.project_dict["uuid"],
                "name_exact": self.TEST_INSTANCE_NAME,
            },
        ).respond(200, json=[self.instance_dict])

    def mock_instance_ready(self):
        respx.get(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/",
        ).respond(200, json=self.instance_dict)

    def test_connect_marketplace_instance_to_multiple_subnets_using_network_syntax(
        self,
    ):
        self.mock_project_lookup()

        self.mock_resource_lookup()

        self.mock_instance_lookup()
        self.mock_instance_ready()

        update_ports_request = respx.post(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/update_ports/",
        ).respond(200, json=self.instance_dict)

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "networks": [
                {"subnet": subnet_name, "floating_ip": "auto"}
                for subnet_name in self.subnets_set
            ],
            "state": "present",
            "wait": True,
            "interval": 20,
            "timeout": 600,
        }
        self.module.check_mode = False

        _, has_changed = waldur_marketplace_os_instance.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(update_ports_request.call_count, 1)

    def test_update_ip_of_marketplace_instance(self):
        self.mock_project_lookup()
        self.mock_resource_lookup()
        self.mock_instance_lookup()
        self.mock_instance_ready()

        respx.post(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/update_ports/",
        ).respond(200, json=self.instance_dict)

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "subnet": self.subnets_set[0],
            "floating_ip": "auto",
            "state": "present",
            "wait": True,
            "interval": 20,
            "timeout": 600,
        }
        self.module.check_mode = False

        _, has_changed = waldur_marketplace_os_instance.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)

    def test_delete_instance(self):
        self.mock_project_lookup()
        self.mock_resource_lookup()
        self.mock_instance_lookup()
        self.mock_instance_ready()

        stop_instance_request = respx.post(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/stop/",
        ).respond(status_code=200)

        terminate_resource_request = respx.post(
            f"{self.API_URL}/api/marketplace-resources/{self.resource_dict['uuid']}/terminate/",
        ).respond(200, json=self.order_uuid_dict)

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "state": "absent",
            "wait": True,
            "interval": 5,
            "timeout": 10,
            "delete_volumes": True,
            "release_floating_ips": True,
        }

        _, has_changed = waldur_marketplace_os_instance.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(stop_instance_request.call_count, 1)
        self.assertEqual(terminate_resource_request.call_count, 1)

    def test_update_security_groups(self):
        self.mock_project_lookup()
        self.mock_resource_lookup()
        self.mock_instance_lookup()
        self.mock_instance_ready()

        update_security_groups_request = respx.post(
            f"{self.API_URL}/api/openstack-instances/{self.instance_dict['uuid']}/update_security_groups/",
        ).respond(200, json=self.instance_dict)

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "state": "present",
            "wait": True,
            "interval": 5,
            "timeout": 600,
            "security_groups": ["web", "ssh"],
        }

        _, has_changed = waldur_marketplace_os_instance.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(update_security_groups_request.call_count, 1)

    def test_create_instance_with_flavor_min_params(self):
        self.mock_project_lookup()
        # First call - no resources (trigger creation)
        respx.get(
            f"{self.API_URL}/api/marketplace-resources/",
            params={
                "project_uuid": self.project_dict["uuid"],
                "name_exact": self.TEST_INSTANCE_NAME,
                "offering_type": "OpenStackTenant.Instance",
            },
        ).mock(
            side_effect=[
                httpx.Response(status_code=200, json=[]),
                httpx.Response(status_code=200, json=[self.resource_dict]),
            ]
        )

        respx.get(
            f"{self.API_URL}/api/marketplace-public-offerings/",
            params={"name_exact": self.TEST_OFFERING_NAME},
        ).respond(200, json=[self.offering_dict])

        create_order_request = respx.post(
            f"{self.API_URL}/api/marketplace-orders/",
        ).respond(201, json=self.order_dict)

        approve_order_request = respx.post(
            f"{self.API_URL}/api/marketplace-orders/{self.order_dict['uuid']}/approve_by_consumer/",
        ).respond(status_code=200)

        respx.get(
            f"{self.API_URL}/api/openstack-instances/",
            params={
                "project_uuid": self.project_dict["uuid"],
                "name_exact": self.TEST_INSTANCE_NAME,
            },
        ).respond(200, json=[self.instance_dict])

        self.mock_instance_ready()

        respx.get(
            f"{self.API_URL}/api/openstack-flavors/",
            params={
                "cores__gte": 2,
                "ram__gte": 1024,
                "o": ["cores", "ram", "disk"],
            },
        ).respond(200, json=[self.flavor_dict])
        respx.get(
            f"{self.API_URL}/api/openstack-images/", params={"name_exact": "test-image"}
        ).respond(200, json=[self.image_dict])

        self.module.params = {
            "api_url": self.API_URL,
            "access_token": "token",
            "name": self.TEST_INSTANCE_NAME,
            "project": self.TEST_PROJECT_NAME,
            "offering": self.TEST_OFFERING_NAME,
            "state": "present",
            "wait": True,
            "interval": 5,
            "timeout": 600,
            "image": "test-image",
            "system_volume_size": 10,
            "subnet": "test-subnet",
            "flavor_min_cpu": 2,
            "flavor_min_ram": 1024,
        }

        _, has_changed = waldur_marketplace_os_instance.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(create_order_request.call_count, 1)
        self.assertEqual(approve_order_request.call_count, 1)
