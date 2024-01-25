from typing import List, Union
from unittest.mock import MagicMock

import pytest
from ldclient import Config, LDClient
from ldclient.evaluation import EvaluationDetail
from ldclient.integrations.test_data import TestData
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import Reason

from ld_openfeature import LaunchDarklyProvider


@pytest.fixture
def test_data_source() -> TestData:
    td = TestData.data_source()
    td.update(td.flag("fallthrough-boolean").variation_for_all(True))
    return td


@pytest.fixture
def evaluation_context() -> EvaluationContext:
    return EvaluationContext('user-key')


@pytest.fixture
def ld_client(test_data_source: TestData) -> LDClient:
    return LDClient(config=Config("example-key", update_processor_class=test_data_source, send_events=False))


@pytest.fixture
def provider(ld_client) -> LaunchDarklyProvider:
    return LaunchDarklyProvider(ld_client)


def test_metadata_name_is_correct(provider: LaunchDarklyProvider):
    assert provider.get_metadata().name == "launchdarkly-openfeature-server"


def test_not_providing_context_returns_error(provider: LaunchDarklyProvider):
    resolution_details = provider.resolve_boolean_details("flag-key", True, None)

    assert resolution_details.value is True
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.TARGETING_KEY_MISSING


def test_evaluation_results_are_converted_to_details(provider: LaunchDarklyProvider, evaluation_context: EvaluationContext):
    resolution_details = provider.resolve_boolean_details("fallthrough-boolean", True, evaluation_context)

    assert resolution_details.value is True
    assert resolution_details.reason == 'FALLTHROUGH'
    assert resolution_details.variant == '0'
    assert resolution_details.error_code is None


def test_evaluation_error_results_are_converted_correctly(ld_client: LDClient, provider: LaunchDarklyProvider, evaluation_context: EvaluationContext):
    detail = EvaluationDetail(True, None, {'kind': 'ERROR', 'errorKind': 'CLIENT_NOT_READY'})
    ld_client.variation_detail = MagicMock(return_value=detail)  # type: ignore[method-assign]

    resolution_details = provider.resolve_boolean_details("flag-key", True, evaluation_context)

    assert resolution_details.value is True
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.PROVIDER_NOT_READY


def test_invalid_types_generate_type_mismatch_results(provider: LaunchDarklyProvider, evaluation_context: EvaluationContext):
    resolution_details = provider.resolve_string_details("fallthrough-boolean", "default-value", evaluation_context)

    assert resolution_details.value == "default-value"
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.TYPE_MISMATCH


@pytest.mark.parametrize(
    "default_value,return_value,expected_value,method_name",
    [
        pytest.param(True, False, False, 'resolve_boolean_details'),
        pytest.param(False, True, True, 'resolve_boolean_details'),
        pytest.param(False, 1, False, 'resolve_boolean_details'),
        pytest.param(False, "True", False, 'resolve_boolean_details'),
        pytest.param(True, [], True, 'resolve_boolean_details'),

        pytest.param('default-string', 'return-string', 'return-string', 'resolve_string_details'),
        pytest.param('default-string', 1, 'default-string', 'resolve_string_details'),
        pytest.param('default-string', True, 'default-string', 'resolve_string_details'),

        pytest.param(1, 2, 2, 'resolve_integer_details'),
        pytest.param(1, True, 1, 'resolve_integer_details'),
        pytest.param(1, False, 1, 'resolve_integer_details'),
        pytest.param(1, "", 1, 'resolve_integer_details'),

        pytest.param(1.0, 2.0, 2.0, 'resolve_float_details'),
        pytest.param(1.0, 2, 2.0, 'resolve_float_details'),
        pytest.param(1.0, True, 1.0, 'resolve_float_details'),
        pytest.param(1.0, 'return-string', 1.0, 'resolve_float_details'),

        pytest.param(['default-value'], ['return-string'], ['return-string'], 'resolve_object_details'),
        pytest.param(['default-value'], True, ['default-value'], 'resolve_object_details'),
        pytest.param(['default-value'], 1, ['default-value'], 'resolve_object_details'),
        pytest.param(['default-value'], 'return-string', ['default-value'], 'resolve_object_details'),
    ],
)
def test_check_method_and_result_match_type(
        # start of parameterized values
        default_value: Union[bool, str, int, float, List],
        return_value: Union[bool, str, int, float, List],
        expected_value: Union[bool, str, int, float, List],
        method_name: str,
        # end of parameterized values
        ld_client: LDClient,
        provider: LaunchDarklyProvider,
        evaluation_context: EvaluationContext):
    detail = EvaluationDetail(return_value, 1, {'kind': 'FALLTHROUGH'})
    ld_client.variation_detail = MagicMock(return_value=detail)  # type: ignore[method-assign]

    method = getattr(provider, method_name)
    resolution_details = method("flag-key", default_value, evaluation_context)

    assert resolution_details.value == expected_value


def test_logger_changes_should_cascade_to_evaluation_converter(provider: LaunchDarklyProvider, caplog):
    _ = provider.resolve_boolean_details("fallthrough-boolean", False, EvaluationContext('user-key', {'kind': False}))

    assert len(caplog.records) == 1
    assert caplog.records[0].message == "'kind' was set to a non-string value; defaulting to user"
