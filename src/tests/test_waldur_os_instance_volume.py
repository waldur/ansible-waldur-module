import unittest
from unittest import mock
import respx

from ansible_waldur_module import waldur_os_instance_volume
from tests.utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models
import ansible_waldur_module.utils as utils


class TestWaldurOsInstanceVolume(unittest.TestCase):
    TEST_PROJECT_NAME = "testname"
    TEST_VOLUME_NAME = "postgresql-data"
    TEST_INSTANCE_NAME = "postgresql-server"

    def setUp(self):
        respx.start()
        self.module = mock.Mock()
        self.project = generate_example_instance(models.Project)
        self.project.name = self.TEST_PROJECT_NAME
        self.project_dict = serialize_attrs_instance(self.project)

        self.volume = generate_example_instance(models.OpenStackVolume)
        self.volume.name = self.TEST_VOLUME_NAME
        self.volume_dict = serialize_attrs_instance(self.volume)

        self.instance = generate_example_instance(models.OpenStackInstance)
        self.instance.name = self.TEST_INSTANCE_NAME
        self.instance_dict = serialize_attrs_instance(self.instance)

        self.module.params = {
            "api_url": "http://example.com:8000",
            "access_token": "token",
            "project": self.TEST_PROJECT_NAME,
            "volume": self.TEST_VOLUME_NAME,
            "instance": self.TEST_INSTANCE_NAME,
            "state": "present",
            "wait": True,
            "interval": 5,
            "timeout": 10,
        }

        self.client = utils.get_client(self.module)

    def tearDown(self):
        respx.stop()

    def mock_project_lookup(self):
        return respx.get(
            "http://example.com:8000/api/projects/",
            params={"name_exact": self.TEST_PROJECT_NAME},
        ).respond(json=[self.project_dict])

    def mock_volume_lookup(self):
        return respx.get(
            "http://example.com:8000/api/openstack-volumes/",
            params={
                "project": self.project_dict["uuid"],
                "name": self.TEST_VOLUME_NAME,
            },
        ).respond(json=[self.volume_dict])

    def mock_instance_lookup(self):
        return respx.get(
            "http://example.com:8000/api/openstack-instances/",
            params={
                "project": self.project_dict["uuid"],
                "name": self.TEST_INSTANCE_NAME,
            },
        ).respond(json=[self.instance_dict])

    def mock_instance_lookup_by_name(self):
        return respx.get(
            "http://example.com:8000/api/openstack-instances/",
            params={
                "project_name": self.TEST_PROJECT_NAME,
                "name": self.TEST_INSTANCE_NAME,
            },
        ).respond(json=[self.instance_dict])

    def test_volume_is_already_attached(self):
        self.mock_project_lookup()
        self.mock_volume_lookup()
        self.mock_instance_lookup()
        self.mock_instance_lookup_by_name()

        self.volume_dict["runtime_state"] = "in-use"
        self.volume_dict["instance"] = self.instance_dict["url"]

        has_changed = waldur_os_instance_volume.send_request_to_waldur(
            self.client, self.module
        )
        self.assertFalse(has_changed)

    def test_volume_is_attached_to_another_instance(self):
        self.volume_dict["runtime_state"] = "in-use"
        self.volume_dict["instance"] = (
            "http://example.com:8000/api/openstack-instances/another-instance/"
        )
        self.mock_project_lookup()
        self.mock_volume_lookup()
        self.mock_instance_lookup()
        self.mock_instance_lookup_by_name()

        respx.get(
            "http://example.com:8000/api/openstack-instances/",
            params={
                "project_name": self.TEST_PROJECT_NAME,
                "name": self.TEST_INSTANCE_NAME,
            },
        ).respond(json=[self.instance_dict])

        respx.post(
            f"http://example.com:8000/api/openstack-volumes/{self.volume_dict['uuid']}/detach/"
        ).respond(status_code=200)

        respx.post(
            f"http://example.com:8000/api/openstack-volumes/{self.volume_dict['uuid']}/attach/",
            json={"instance": self.instance_dict["url"]},
        ).respond(status_code=200)

        has_changed = waldur_os_instance_volume.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)

    def test_volume_is_available(self):
        self.volume_dict["runtime_state"] = "available"
        self.mock_project_lookup()
        self.mock_volume_lookup()
        self.mock_instance_lookup()
        self.mock_instance_lookup_by_name()

        attach_response = respx.post(
            f"http://example.com:8000/api/openstack-volumes/{self.volume_dict['uuid']}/attach/",
            json={"instance": self.instance_dict["url"]},
        ).respond(status_code=200)

        has_changed = waldur_os_instance_volume.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(attach_response.call_count, 1)

    def test_volume_detach(self):
        self.module.params["state"] = "absent"
        self.volume_dict["runtime_state"] = "in-use"
        self.mock_project_lookup()
        self.mock_volume_lookup()
        self.mock_instance_lookup()
        self.mock_instance_lookup_by_name()
        self.instance_dict["state"] = "OK"
        respx.get(
            f"http://example.com:8000/api/openstack-instances/{self.instance_dict['uuid']}/"
        ).respond(json=self.instance_dict)
        detach_response = respx.post(
            f"http://example.com:8000/api/openstack-volumes/{self.volume_dict['uuid']}/detach/"
        ).respond(status_code=200)
        self.volume_dict["state"] = "OK"
        respx.get(
            f"http://example.com:8000/api/openstack-volumes/{self.volume_dict['uuid']}/"
        ).respond(json=self.volume_dict)
        has_changed = waldur_os_instance_volume.send_request_to_waldur(
            self.client, self.module
        )
        self.assertTrue(has_changed)
        self.assertEqual(detach_response.call_count, 1)

    def test_volume_already_detached(self):
        self.module.params["state"] = "absent"
        self.volume_dict["runtime_state"] = "available"
        self.mock_project_lookup()
        self.mock_volume_lookup()
        self.mock_instance_lookup()
        self.mock_instance_lookup_by_name()

        has_changed = waldur_os_instance_volume.send_request_to_waldur(
            self.client, self.module
        )
        self.assertFalse(has_changed)
