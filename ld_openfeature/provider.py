import threading
from typing import Any, List, Mapping, Optional, Sequence, Union

from ldclient.evaluation import EvaluationDetail
from ldclient import LDClient, Config
from ldclient.interfaces import DataSourceStatus, FlagChange, DataSourceState
from openfeature.evaluation_context import EvaluationContext
from openfeature.exception import ErrorCode, ProviderFatalError
from openfeature.flag_evaluation import FlagResolutionDetails, FlagType, FlagValueType, Reason
from openfeature.hook import Hook
from openfeature.provider.metadata import Metadata
from openfeature.provider import AbstractProvider
from openfeature.event import ProviderEventDetails

from ld_openfeature.impl.context_converter import EvaluationContextConverter
from ld_openfeature.impl.details_converter import ResolutionDetailsConverter


class LaunchDarklyProvider(AbstractProvider):
    def __init__(self, config: Config):
        self.__client = LDClient(config)

        self.__context_converter = EvaluationContextConverter()
        self.__details_converter = ResolutionDetailsConverter()

    @property
    def client(self) -> LDClient:
        """
        Access the underlying LaunchDarky client instance backing this provider.

        This is useful for accessing additional functionality not exposed by the provider.
        """
        return self.__client

    def __handle_data_source_status(self, status: DataSourceStatus):
        state = status.state
        if state == DataSourceState.INITIALIZING:
            return
        elif state == DataSourceState.VALID:
            self.emit_provider_ready(ProviderEventDetails())
        elif state == DataSourceState.OFF:
            error_message = self.__get_message(status,
                                               "the provider has encountered a permanent error or has been shutdown")
            self.emit_provider_error(ProviderEventDetails(error_code=ErrorCode.PROVIDER_FATAL,
                                                          message=error_message))
        elif state == DataSourceState.INTERRUPTED:
            error_message = self.__get_message(status, "encountered an unknown error")
            self.emit_provider_stale(ProviderEventDetails(message=error_message))

        # For now treat an unknown state as no change.

    def __handle_flag_change(self, change: FlagChange):
        self.emit_provider_configuration_changed(ProviderEventDetails(flags_changed=[change.key]))
        pass

    def initialize(self, evaluation_context: EvaluationContext):
        ready_event = threading.Event()

        def ready_handler(status: DataSourceStatus):
            if status.state == DataSourceState.VALID:
                ready_event.set()
            elif status.state == DataSourceState.OFF:
                ready_event.set()

        # We listen just to handle the ready event. We do not emit events because the client emits them for us.
        self.__client.data_source_status_provider.add_listener(ready_handler)

        # Check for conditions that may have happened before we added the listener.
        if self.__client.data_source_status_provider.status.state == DataSourceState.OFF:
            ready_event.set()

        if self.__client.is_initialized():
            ready_event.set()

        ready_event.wait()

        self.__client.data_source_status_provider.remove_listener(ready_handler)

        if not self.__client.is_initialized():
            raise ProviderFatalError(error_message="launchdarkly client initialization failed")

        # Listen to new status events and emit them.
        self.__client.data_source_status_provider.add_listener(self.__handle_data_source_status)
        self.__client.flag_tracker.add_listener(self.__handle_flag_change)

    def shutdown(self):
        self.__client.data_source_status_provider.remove_listener(self.__handle_data_source_status)
        self.__client.flag_tracker.remove_listener(self.__handle_flag_change)
        self.__client.close()

    def get_metadata(self) -> Metadata:
        return Metadata("launchdarkly-openfeature-server")

    def get_provider_hooks(self) -> List[Hook]:
        return []

    def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        """Resolves the flag value for the provided flag key as a boolean"""
        return self.__resolve_value(FlagType(FlagType.BOOLEAN), flag_key, default_value, evaluation_context)

    def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        """Resolves the flag value for the provided flag key as a string"""
        return self.__resolve_value(FlagType(FlagType.STRING), flag_key, default_value, evaluation_context)

    def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        """Resolves the flag value for the provided flag key as a integer"""
        return self.__resolve_value(FlagType(FlagType.INTEGER), flag_key, default_value, evaluation_context)

    def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        """Resolves the flag value for the provided flag key as a float"""
        return self.__resolve_value(FlagType(FlagType.FLOAT), flag_key, default_value, evaluation_context)

    def resolve_object_details(
        self,
        flag_key: str,
        default_value: Union[
            Sequence[FlagValueType], Mapping[str, FlagValueType]
        ],
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[Union[dict, list]]:
        """Resolves the flag value for the provided flag key as a list or dictionary"""
        return self.__resolve_value(FlagType(FlagType.OBJECT), flag_key, default_value, evaluation_context)

    def __resolve_value(self, flag_type: FlagType, flag_key: str, default_value: Any,
                        evaluation_context: Optional[EvaluationContext] = None) -> FlagResolutionDetails:
        if evaluation_context is None:
            return FlagResolutionDetails(
                value=default_value,
                reason=Reason(Reason.ERROR),
                error_code=ErrorCode.TARGETING_KEY_MISSING
            )

        ld_context = self.__context_converter.to_ld_context(evaluation_context)
        result = self.__client.variation_detail(flag_key, ld_context, default_value)

        resolved_value = self.__validate_and_cast_value(flag_type, result.value)
        if resolved_value is None:
            return self.__mismatched_type_details(default_value)

        resolved_detail = EvaluationDetail(
            value=resolved_value,
            variation_index=result.variation_index,
            reason=result.reason,
        )

        return self.__details_converter.to_resolution_details(resolved_detail)

    def __validate_and_cast_value(self, flag_type: FlagType, value: Any):
        """Serializes the raw flag value to the expected type based on flag_type."""
        if flag_type == FlagType.BOOLEAN and isinstance(value, bool):
                return value
        elif flag_type == FlagType.STRING and isinstance(value, str):
                return value
        elif flag_type == FlagType.INTEGER and isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value) # Float decimals are truncated to int
        elif flag_type == FlagType.FLOAT and isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        elif flag_type == FlagType.OBJECT and isinstance(value, (dict, list)):
                return value
        return None

    @staticmethod
    def __mismatched_type_details(default_value: Any) -> FlagResolutionDetails:
        return FlagResolutionDetails(
            value=default_value,
            reason=Reason(Reason.ERROR),
            error_code=ErrorCode.TYPE_MISMATCH
        )

    @staticmethod
    def __get_message(status: DataSourceStatus, default: str):
        if status.error and status.error.message:
            return status.error.message
        return default
