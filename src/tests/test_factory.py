import pytest
from .utils.factory import generate_example_instance, serialize_attrs_instance
import waldur_api_client.models as models
import json


@pytest.mark.parametrize(
    "model_class",
    [
        models.Project,
        models.Offering,
        models.OpenStackSecurityGroup,
        models.OpenStackTenant,
    ],
)
def test_multiple_models_serialization_cycle(model_class):
    """Test serialization-deserialization cycle for multiple model types."""
    original_instance = generate_example_instance(model_class)

    instance_dict = serialize_attrs_instance(original_instance)

    json_str = json.dumps(instance_dict)
    instance_dict = json.loads(json_str)
    reconstructed_instance = model_class.from_dict(instance_dict)
    assert isinstance(reconstructed_instance, model_class)
