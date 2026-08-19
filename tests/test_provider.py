import threading
import time
from typing import List, Union
from unittest.mock import patch

import pytest
from ldclient import LDClient
from ldclient.evaluation import EvaluationDetail
from ldclient.integrations.test_data import TestData
from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEvent, EventDetails
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import Reason
from openfeature.provider import ProviderStatus
from openfeature.track import TrackingEventDetails
from openfeature import api

from ld_openfeature import LaunchDarklyProvider, Config
from tests.test_data_sources import FailingDataSource, InitializedThenFailingDataSource, StaleDataSource, UpdatingDataSource, DelayedFailingDataSource


@pytest.fixture
def test_data_source() -> TestData:
    td = TestData.data_source()
    td.update(td.flag("fallthrough-boolean").variation_for_all(True))
    return td


@pytest.fixture
def evaluation_context() -> EvaluationContext:
    return EvaluationContext('user-key')


@pytest.fixture
def config(test_data_source: TestData) -> Config:
    return Config("example-key", update_processor_class=test_data_source, send_events=False)


@pytest.fixture
def provider(config) -> LaunchDarklyProvider:
    return LaunchDarklyProvider(config)


def test_metadata_name_is_correct(provider: LaunchDarklyProvider):
    assert provider.get_metadata().name == "launchdarkly-openfeature-server"


def test_ldclient_is_accessible(provider: LaunchDarklyProvider):
    assert type(provider.client) is LDClient


def test_not_providing_context_returns_error(provider: LaunchDarklyProvider):
    resolution_details = provider.resolve_boolean_details("flag-key", True, None)

    assert resolution_details.value is True
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.TARGETING_KEY_MISSING


def test_evaluation_results_are_converted_to_details(provider: LaunchDarklyProvider,
                                                     evaluation_context: EvaluationContext):
    resolution_details = provider.resolve_boolean_details("fallthrough-boolean", True, evaluation_context)

    assert resolution_details.value is True
    assert resolution_details.reason == 'FALLTHROUGH'
    assert resolution_details.variant == '0'
    assert resolution_details.error_code is None


def test_evaluation_error_results_are_converted_correctly(provider: LaunchDarklyProvider,
                                                          evaluation_context: EvaluationContext):
    detail = EvaluationDetail(True, None, {'kind': 'ERROR', 'errorKind': 'CLIENT_NOT_READY'})
    with patch.object(LDClient, 'variation_detail', lambda self, _key, _context, _default: detail):
        resolution_details = provider.resolve_boolean_details("flag-key", True, evaluation_context)

    assert resolution_details.value is True
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.PROVIDER_NOT_READY


def test_invalid_types_generate_type_mismatch_results(provider: LaunchDarklyProvider,
                                                      evaluation_context: EvaluationContext):
    resolution_details = provider.resolve_string_details("fallthrough-boolean", "default-value", evaluation_context)

    assert resolution_details.value == "default-value"
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.variant is None
    assert resolution_details.error_code == ErrorCode.TYPE_MISMATCH


@pytest.mark.parametrize(
    "default_value,return_value,expected_value,expected_type,method_name",
        [
        pytest.param(True, False, False, bool, 'resolve_boolean_details'),
        pytest.param(False, True, True, bool, 'resolve_boolean_details'),
        pytest.param(False, 1, False, bool, 'resolve_boolean_details'),
        pytest.param(False, "True", False, bool, 'resolve_boolean_details'),
        pytest.param(True, [], True, bool, 'resolve_boolean_details'),

        pytest.param('default-string', 'return-string', 'return-string', str, 'resolve_string_details'),
        pytest.param('default-string', 1, 'default-string', str, 'resolve_string_details'),
        pytest.param('default-string', True, 'default-string', str, 'resolve_string_details'),

        pytest.param(1, 2, 2, int, 'resolve_integer_details'),
        pytest.param(1, True, 1, int, 'resolve_integer_details'),
        pytest.param(1, False, 1, int, 'resolve_integer_details'),
        pytest.param(1, "", 1, int, 'resolve_integer_details'),
        pytest.param(1, 2.9, 2, int, 'resolve_integer_details'),

        pytest.param(1.0, 2.0, 2.0, float, 'resolve_float_details'),
        pytest.param(1.0, 2, 2.0, float, 'resolve_float_details'),
        pytest.param(1.0, True, 1.0, float, 'resolve_float_details'),
        pytest.param(1.0, 'return-string', 1.0, float, 'resolve_float_details'),

        pytest.param(['default-value'], ['return-string'], ['return-string'], list, 'resolve_object_details'),
        pytest.param(['default-value'], True, ['default-value'], list, 'resolve_object_details'),
        pytest.param(['default-value'], 1, ['default-value'], list, 'resolve_object_details'),
        pytest.param(['default-value'], 'return-string', ['default-value'], list, 'resolve_object_details'),

        pytest.param({'key': 'default'}, {'key': 'return'}, {'key': 'return'}, dict, 'resolve_object_details'),
        pytest.param({'key': 'default'}, True, {'key': 'default'}, dict, 'resolve_object_details'),
        pytest.param({'key': 'default'}, 1, {'key': 'default'}, dict, 'resolve_object_details'),
        pytest.param({'key': 'default'}, 'return-string', {'key': 'default'}, dict, 'resolve_object_details'),
    ],
)
def test_check_method_and_result_match_type(
        # start of parameterized values
        default_value: Union[bool, str, int, float, List],
        return_value: Union[bool, str, int, float, List],
        expected_value: Union[bool, str, int, float, List],
        expected_type: type,
        method_name: str,
        # end of parameterized values
        test_data_source: TestData,
        provider: LaunchDarklyProvider,
        evaluation_context: EvaluationContext):
    test_data_source.update(test_data_source.flag("check-method-flag").variations(return_value).variation_for_all(0))

    method = getattr(provider, method_name)
    resolution_details = method("check-method-flag", default_value, evaluation_context)

    assert resolution_details.value == expected_value
    #assert isinstance(resolution_details.value, expected_type)


def test_logger_changes_should_cascade_to_evaluation_converter(provider: LaunchDarklyProvider, caplog):
    _ = provider.resolve_boolean_details("fallthrough-boolean", False, EvaluationContext('user-key', {'kind': False}))

    assert len(caplog.records) == 1
    assert caplog.records[0].message == "'kind' was set to a non-string value; defaulting to user"


def test_track_without_context_does_not_send_an_event(provider: LaunchDarklyProvider):
    with patch.object(LDClient, 'track') as mock_track:
        provider.track("metric-key", None, None)

    mock_track.assert_not_called()


def test_track_without_details_sends_event_without_data(provider: LaunchDarklyProvider,
                                                        evaluation_context: EvaluationContext):
    with patch.object(LDClient, 'track') as mock_track:
        provider.track("metric-key", evaluation_context, None)

    mock_track.assert_called_once()
    name, context = mock_track.call_args.args
    assert name == "metric-key"
    assert context.key == 'user-key'


def test_track_sends_attributes_as_data(provider: LaunchDarklyProvider,
                                        evaluation_context: EvaluationContext):
    with patch.object(LDClient, 'track') as mock_track:
        provider.track("metric-key", evaluation_context, TrackingEventDetails(attributes={'string': 'value'}))

    mock_track.assert_called_once()
    name, context, data = mock_track.call_args.args
    assert name == "metric-key"
    assert context.key == 'user-key'
    assert data == {'string': 'value'}


def test_track_sends_value_as_metric_value(provider: LaunchDarklyProvider,
                                           evaluation_context: EvaluationContext):
    with patch.object(LDClient, 'track') as mock_track:
        provider.track("metric-key", evaluation_context,
                       TrackingEventDetails(value=17, attributes={'string': 'value'}))

    mock_track.assert_called_once()
    name, context, data, metric_value = mock_track.call_args.args
    assert name == "metric-key"
    assert context.key == 'user-key'
    assert data == {'string': 'value'}
    assert metric_value == 17


def test_track_without_attributes_sends_metric_value_without_data(provider: LaunchDarklyProvider,
                                                                  evaluation_context: EvaluationContext):
    with patch.object(LDClient, 'track') as mock_track:
        provider.track("metric-key", evaluation_context, TrackingEventDetails(value=17))

    mock_track.assert_called_once()
    name, context, data, metric_value = mock_track.call_args.args
    assert data is None
    assert metric_value == 17


def test_provider_emits_ready_event_when_immediately_ready():
    emission_count = 0
    lock = threading.Lock()
    thread_event = threading.Event()

    def handle_status(details: EventDetails):
        if details.provider_name == 'launchdarkly-openfeature-server':
            nonlocal emission_count
            with lock:
                emission_count += 1
            thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_READY, handle_status)

    openfeature_provider = LaunchDarklyProvider(Config("", offline=True))
    api.set_provider(openfeature_provider)

    assert thread_event.wait(timeout=5)
    time.sleep(0.1)

    with lock:
        assert emission_count == 1

    api.shutdown()


def test_provider_emits_error_event_immediately_failed():
    emission_count = 0
    lock = threading.Lock()
    thread_event = threading.Event()

    def handle_status(details: EventDetails):
        if details.provider_name == 'launchdarkly-openfeature-server':
            nonlocal emission_count
            with lock:
                emission_count += 1
            thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_ERROR, handle_status)

    openfeature_provider = LaunchDarklyProvider(
        Config("", update_processor_class=FailingDataSource, send_events=False))

    api.set_provider(openfeature_provider)

    assert thread_event.wait(timeout=5)
    time.sleep(0.1)

    with lock:
        assert emission_count == 1

    api.shutdown()


def test_provider_emits_error_event_delayed_failure():
    emission_count = 0
    lock = threading.Lock()
    thread_event = threading.Event()

    def handle_status(details: EventDetails):
        if details.provider_name == 'launchdarkly-openfeature-server':
            nonlocal emission_count
            with lock:
                emission_count += 1
            thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_ERROR, handle_status)

    openfeature_provider = LaunchDarklyProvider(
        Config("", update_processor_class=DelayedFailingDataSource, send_events=False))

    api.set_provider(openfeature_provider)

    assert thread_event.wait(timeout=5)
    time.sleep(0.1)

    with lock:
        assert emission_count == 1

    api.shutdown()


def test_evaluations_continue_after_the_data_source_permanently_fails():
    thread_event = threading.Event()

    def handle_status(details: EventDetails):
        if details.provider_name == 'launchdarkly-openfeature-server':
            thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_ERROR, handle_status)

    provider = LaunchDarklyProvider(
        Config("", update_processor_class=InitializedThenFailingDataSource, send_events=False))
    api.set_provider(provider)
    client = api.get_client()

    assert thread_event.wait(timeout=5)

    assert client.get_provider_status() == ProviderStatus.ERROR
    assert client.get_boolean_value("cached-boolean", False, EvaluationContext('user-key')) is True

    api.shutdown()


def test_provider_emits_stale_event():
    thread_event = threading.Event()

    def handle_status(details: EventDetails):
        if details.provider_name == 'launchdarkly-openfeature-server':
            thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_STALE, handle_status)

    openfeature_provider = LaunchDarklyProvider(Config("", update_processor_class=StaleDataSource, send_events=False))
    api.set_provider(openfeature_provider)

    assert thread_event.wait(timeout=5)

    api.shutdown()


def test_provider_emits_configuration_event():
    thread_event = threading.Event()

    provider = LaunchDarklyProvider(Config("", update_processor_class=UpdatingDataSource, send_events=False))

    def handle_change(details: EventDetails):
        assert details.flags_changed is not None
        assert len(details.flags_changed) == 1
        assert details.flags_changed[0] == "potato"
        thread_event.set()

    api.add_handler(ProviderEvent.PROVIDER_CONFIGURATION_CHANGED, handle_change)
    api.set_provider(provider)

    assert thread_event.wait(timeout=5)

    api.shutdown()
