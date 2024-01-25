from typing import Optional, Union

import pytest
from ldclient.evaluation import EvaluationDetail
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import Reason

from ld_openfeature.impl.details_converter import ResolutionDetailsConverter


@pytest.fixture
def details_converter() -> ResolutionDetailsConverter:
    return ResolutionDetailsConverter()


@pytest.mark.parametrize(
    'detail_kind,reason',
    [
        pytest.param('OFF', Reason.DISABLED),
        pytest.param('TARGET_MATCH', Reason.TARGETING_MATCH),
        pytest.param('ERROR', Reason.ERROR),
        pytest.param('FALLTHROUGH', 'FALLTHROUGH'),
        pytest.param('RULE_MATCH', 'RULE_MATCH'),
        pytest.param('PREREQUISITE_FAILED', 'PREREQUISITE_FAILED'),
    ],
)
def test_ld_to_openfeature_kind_mappings(detail_kind: str, reason: Union[str, Reason], details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, None, {'kind': detail_kind})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.reason == reason


@pytest.mark.parametrize(
    'error_kind,error_code',
    [
        pytest.param(None, ErrorCode.GENERAL),
        pytest.param('CLIENT_NOT_READY', ErrorCode.PROVIDER_NOT_READY),
        pytest.param('FLAG_NOT_FOUND', ErrorCode.FLAG_NOT_FOUND),
        pytest.param('MALFORMED_FLAG', ErrorCode.PARSE_ERROR),
        pytest.param('USER_NOT_SPECIFIED', ErrorCode.TARGETING_KEY_MISSING),
        pytest.param('EXCEPTION_ERROR', ErrorCode.GENERAL),
    ],
)
def test_ld_to_openfeature_error_kind_mappings(error_kind: Optional[str], error_code: ErrorCode, details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, None, {'kind': 'ERROR', 'errorKind': error_kind})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.error_code == error_code
