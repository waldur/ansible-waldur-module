import attr
import random
from faker import Faker
from typing import Any, get_args, get_origin, Union, ForwardRef, Dict
import uuid
import enum
import datetime
from waldur_api_client.types import Unset
import waldur_api_client.models as models

fake = Faker()

UNSET = Unset


MODEL_REGISTRY = {
    cls.__name__: cls for cls in vars(models).values() if isinstance(cls, type)
}


def serialize_attrs_instance(instance):
    """Convert an attrs instance to a dict with proper UUID serialization."""
    return attr.asdict(
        instance,
        value_serializer=serialize_value,
        filter=lambda attr, value: attr.name != "additional_properties",
    )


def serialize_value(inst, attr, value):
    """Serialize values for JSON compatibility."""
    if isinstance(value, Unset):
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, datetime.datetime):
        return value.isoformat()
    return value


def generate_value(attr_type: Any) -> Any:
    # Type handling
    origin = get_origin(attr_type)
    args = get_args(attr_type)
    if origin is None:
        if isinstance(attr_type, ForwardRef):
            ref_name = attr_type.__forward_arg__
            ref_cls = MODEL_REGISTRY.get(ref_name)
            if ref_cls:
                return generate_example_instance(ref_cls)
            else:
                return {}
        if attr_type == str:
            return fake.word()
        elif attr_type == int:
            return random.randint(1, 100)
        elif attr_type == float:
            return random.uniform(1.0, 100.0)
        elif attr_type == bool:
            return random.choice([True, False])
        elif attr_type == uuid.UUID:
            return uuid.uuid4()
        elif attr_type == datetime.datetime:
            return datetime.datetime.now(datetime.timezone.utc)
        elif attr_type == datetime.date:
            return datetime.date.today().isoformat()

        elif attr.has(attr_type):
            # Nested attrs
            return generate_example_instance(attr_type)
        elif isinstance(attr_type, type) and issubclass(attr_type, enum.Enum):
            # If it's an enum, pick a random value
            return random.choice(list(attr_type))
    elif origin is list:
        return []
    elif origin in (dict, Dict):
        return {}
    elif origin is Union:
        if type(None) in args:
            # Optional[...] → select not None
            non_none_args = [a for a in args if a is not type(None)]
            return generate_value(non_none_args[0])
        elif datetime.datetime in args:
            return datetime.datetime.now(datetime.timezone.utc)
        elif datetime.date in args:
            return datetime.date.today().isoformat()
        elif UNSET in args:
            # Union[Unset, T] → select T
            non_unset_args = [a for a in args if a is not UNSET]
            return generate_value(non_unset_args[0])
        elif uuid.UUID in args:
            return uuid.uuid4()
        elif datetime.datetime in args:
            return datetime.datetime.now(datetime.timezone.utc)
        elif any(issubclass(arg, enum.Enum) for arg in args if isinstance(arg, type)):
            enum_type = next(
                arg
                for arg in args
                if isinstance(arg, type) and issubclass(arg, enum.Enum)
            )
            return random.choice(list(enum_type))
        elif any(isinstance(arg, ForwardRef) for arg in args):
            # For ForwardRef, we'll return empty dict for now
            return {}
    return Unset()


def generate_example_instance(cls: Any) -> Any:
    values = {}
    for field in attr.fields(cls):
        if field.name == "additional_properties":
            continue
        values[field.name] = generate_value(field.type)
    return cls(**values)
