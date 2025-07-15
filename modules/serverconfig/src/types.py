from typing import TypeGuard

from .converters import (AllRepresentation, EnumOptionRepresentation,
                         FloatOptionRepresentation, IntOptionRepresentation)


def is_number_option_representation(
    representation: AllRepresentation,
) -> TypeGuard[IntOptionRepresentation | FloatOptionRepresentation]:
    """
    Check if the given representation is a number option representation.
    """
    return representation["type"] in ("int", "float")

def is_enum_option_representation(
    representation: AllRepresentation,
) -> TypeGuard[EnumOptionRepresentation]:
    """
    Check if the given representation is an EnumOptionRepresentation.
    """
    return representation["type"] == "enum"