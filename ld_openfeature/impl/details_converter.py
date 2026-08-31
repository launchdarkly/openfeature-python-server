from typing import Any, Dict, Mapping, Optional, Union

from ldclient.evaluation import EvaluationDetail
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import (
    FlagMetadata,
    FlagResolutionDetails,
    Reason,
)

_VARIATION_INDEX_KEY = 'variationIndex'
_IN_EXPERIMENT_KEY = 'inExperiment'
_RULE_INDEX_KEY = 'ruleIndex'
_RULE_ID_KEY = 'ruleId'
_PREREQUISITE_KEY_KEY = 'prerequisiteKey'
_BIG_SEGMENTS_STATUS_KEY = 'bigSegmentsStatus'


class ResolutionDetailsConverter:
    def to_resolution_details(self, result: EvaluationDetail) -> FlagResolutionDetails:
        value = result.value
        is_default = result.is_default_value()
        variation_index = result.variation_index

        reason = result.reason
        reason_kind = reason.get('kind')
        reason_kind = reason_kind if isinstance(reason_kind, str) else ''

        openfeature_reason = self.__kind_to_reason(reason_kind)

        openfeature_error_code: Optional[ErrorCode] = None
        if reason_kind == "ERROR":
            openfeature_error_code = self.__error_kind_to_code(reason.get('errorKind'))

        openfeature_variant: Optional[str] = None
        if not is_default:
            openfeature_variant = str(variation_index)

        return FlagResolutionDetails(
            value=value,
            error_code=openfeature_error_code,
            error_message=None,
            reason=openfeature_reason,
            variant=openfeature_variant,
            flag_metadata=self.__to_flag_metadata(reason, variation_index if not is_default else None),
        )

    @staticmethod
    def __to_flag_metadata(reason: Mapping[str, Any], variation_index: Optional[int]) -> FlagMetadata:
        metadata: Dict[str, Union[bool, int, float, str]] = {}

        if variation_index is not None:
            metadata[_VARIATION_INDEX_KEY] = variation_index

        if reason.get('inExperiment') is True:
            metadata[_IN_EXPERIMENT_KEY] = True

        rule_index = reason.get('ruleIndex')
        if isinstance(rule_index, int):
            metadata[_RULE_INDEX_KEY] = rule_index

        rule_id = reason.get('ruleId')
        if isinstance(rule_id, str):
            metadata[_RULE_ID_KEY] = rule_id

        prerequisite_key = reason.get('prerequisiteKey')
        if isinstance(prerequisite_key, str):
            metadata[_PREREQUISITE_KEY_KEY] = prerequisite_key

        big_segments_status = reason.get('bigSegmentsStatus')
        if isinstance(big_segments_status, str):
            metadata[_BIG_SEGMENTS_STATUS_KEY] = big_segments_status

        return metadata

    @staticmethod
    def __kind_to_reason(kind: str) -> str:
        if kind == 'OFF':
            return Reason.DISABLED
        elif kind == 'TARGET_MATCH':
            return Reason.TARGETING_MATCH
        elif kind == 'ERROR':
            return Reason.ERROR

        # NOTE: FALLTHROUGH, RULE_MATCH, PREREQUISITE_FAILED intentionally
        # omitted

        return kind

    @staticmethod
    def __error_kind_to_code(error_kind: Optional[str]) -> ErrorCode:
        if error_kind is None:
            return ErrorCode.GENERAL

        if error_kind == 'CLIENT_NOT_READY':
            return ErrorCode.PROVIDER_NOT_READY
        elif error_kind == 'FLAG_NOT_FOUND':
            return ErrorCode.FLAG_NOT_FOUND
        elif error_kind == 'MALFORMED_FLAG':
            return ErrorCode.PARSE_ERROR
        elif error_kind == 'USER_NOT_SPECIFIED':
            return ErrorCode.TARGETING_KEY_MISSING
        elif error_kind == 'WRONG_TYPE':
            return ErrorCode.TYPE_MISMATCH

        # NOTE: EXCEPTION_ERROR intentionally omitted

        return ErrorCode.GENERAL
