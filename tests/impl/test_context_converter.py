import pytest
from openfeature.evaluation_context import EvaluationContext

from ld_openfeature.impl.context_converter import EvaluationContextConverter


@pytest.fixture
def context_converter() -> EvaluationContextConverter:
    return EvaluationContextConverter()


def test_create_context_with_only_targeting_key(context_converter: EvaluationContextConverter):
    context = EvaluationContext("user-key")
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'
    assert ld_context.kind == 'user'


def test_create_context_with_invalid_key(context_converter: EvaluationContextConverter, caplog):
    context = EvaluationContext(None, {"key": False})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is False
    assert ld_context.key == ''

    assert caplog.records[0].message == "A non-string 'key' attribute was provided."


def test_create_context_with_invalid_targeting_key(context_converter: EvaluationContextConverter, caplog):
    context = EvaluationContext(False)  # type: ignore[arg-type]
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is False
    assert ld_context.key == ''

    assert caplog.records[0].message == "The EvaluationContext must contain either a 'targetingKey' or a 'key' and the type must be a string."


def test_invalid_private_attribute_types_are_ignored(context_converter: EvaluationContextConverter, caplog):
    context = EvaluationContext("user-key", {"privateAttributes": [True]})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'

    assert caplog.records[0].message == "'privateAttributes' must be an array of only string values"


def test_create_multi_context_with_invalid_targeting_key(context_converter: EvaluationContextConverter):
    attributes = {
        'kind': 'multi',
        'user': {'targetingKey': False, 'key': 'user-key', 'name': 'User name'},
        'org': {'key': 'org-key', 'name': 'Org name'},
    }
    context = EvaluationContext(None, attributes)
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'org-key'
    assert ld_context.kind == 'org'


def test_create_context_with_only_key(context_converter: EvaluationContextConverter):
    context = EvaluationContext(None, {"key": "user-key"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'
    assert ld_context.kind == 'user'


def test_targeting_key_takes_precedence_over_attribute_key(context_converter: EvaluationContextConverter):
    context = EvaluationContext("should-use", {"kind": "org", "key": "do-not-use"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'should-use'
    assert ld_context.kind == 'org'


def test_targeting_key_in_attributes_is_ignored(context_converter: EvaluationContextConverter):
    context = EvaluationContext("should-use", {"kind": "org", "key": "do-not-use", "targetingKey": "also-do-not-use"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'should-use'
    assert ld_context.kind == 'org'


def test_create_context_with_key_and_kind(context_converter: EvaluationContextConverter):
    context = EvaluationContext("org-key", {"kind": "org"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'org-key'
    assert ld_context.kind == 'org'


def test_invalid_kind_resets_to_user(context_converter: EvaluationContextConverter):
    context = EvaluationContext("org-key", {"kind": False})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'org-key'
    assert ld_context.kind == 'user'


def test_attributes_are_referenced_correctly(context_converter: EvaluationContextConverter):
    context = EvaluationContext("user-key", {"kind": "user", "anonymous": True, "name": "Sandy", "lastName": "Beaches"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'
    assert ld_context.kind == 'user'
    assert ld_context.anonymous is True
    assert ld_context.name == 'Sandy'
    assert ld_context.get('lastName') == 'Beaches'


def test_invalid_attributes_are_ignored(context_converter: EvaluationContextConverter):
    context = EvaluationContext("user-key", {"kind": "user", "anonymous": "True", "name": 30, "privateAttributes": "testing"})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'
    assert ld_context.kind == 'user'
    assert ld_context.anonymous is False
    assert ld_context.name is None
    assert ld_context.private_attributes == ()


def test_private_attributes_are_processed_correctly(context_converter: EvaluationContextConverter):
    context = EvaluationContext("user-key", {"kind": "user", "address": {"street": "123 Easy St", "city": "Anytown"}, "name": "Sandy", "privateAttributes": ["name", "/address/city"]})
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.key == 'user-key'
    assert ld_context.kind == 'user'
    assert ld_context.private_attributes == ["name", "/address/city"]


def test_can_create_multi_kind_context(context_converter: EvaluationContextConverter):
    attributes = {
        'kind': 'multi',
        'user': {'key': 'user-key', 'name': 'User name'},
        'org': {'key': 'org-key', 'name': 'Org name'},
    }
    context = EvaluationContext(None, attributes)
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.multiple is True

    user_context = ld_context.get_individual_context('user')
    assert user_context is not None
    assert user_context.key == 'user-key'
    assert user_context.kind == 'user'
    assert user_context.name == 'User name'

    org_context = ld_context.get_individual_context('org')
    assert org_context is not None
    assert org_context.key == 'org-key'
    assert org_context.kind == 'org'
    assert org_context.name == 'Org name'


def test_can_multi_kind_ignores_kind_attribute(context_converter: EvaluationContextConverter):
    attributes = {
        'kind': 'multi',
        'user': {'key': 'user-key', 'kind': 'device', 'name': 'User name'},
        'org': {'key': 'org-key', 'name': 'Org name'},
    }
    context = EvaluationContext(None, attributes)
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.multiple is True

    user_context = ld_context.get_individual_context('user')
    assert user_context is not None
    assert user_context.key == 'user-key'
    assert user_context.kind == 'user'
    assert user_context.name == 'User name'

    org_context = ld_context.get_individual_context('org')
    assert org_context is not None
    assert org_context.key == 'org-key'
    assert org_context.kind == 'org'
    assert org_context.name == 'Org name'


def test_multi_context_discards_invalid_single_kind(context_converter: EvaluationContextConverter):
    attributes = {
        'kind': 'multi',
        'user': False,
        'org': {'key': 'org-key', 'name': 'Org name'},
    }
    context = EvaluationContext(None, attributes)
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is True
    assert ld_context.multiple is False
    assert ld_context.key == 'org-key'
    assert ld_context.kind == 'org'
    assert ld_context.name == 'Org name'


def test_handles_invalid_nested_contexts(context_converter: EvaluationContextConverter):
    attributes = {
        'kind': 'multi',
        'user': 'invalid format',
        'org': False
    }
    context = EvaluationContext(None, attributes)
    ld_context = context_converter.to_ld_context(context)

    assert ld_context.valid is False
    assert ld_context.multiple is False
