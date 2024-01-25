from typing import Optional

from ldclient.evaluation import EvaluationDetail
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import FlagResolutionDetails, Reason


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
            variant=openfeature_variant
            # flag_metadata = FlagMetadata = field(default_factory=dict)
        )
        pass

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

        # NOTE: EXCEPTION_ERROR intentionally omitted

        return ErrorCode.GENERAL
