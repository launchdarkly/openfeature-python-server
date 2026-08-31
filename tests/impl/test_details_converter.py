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
        pytest.param('WRONG_TYPE', ErrorCode.TYPE_MISMATCH),
        pytest.param('EXCEPTION_ERROR', ErrorCode.GENERAL),
    ],
)
def test_ld_to_openfeature_error_kind_mappings(error_kind: Optional[str], error_code: ErrorCode, details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, None, {'kind': 'ERROR', 'errorKind': error_kind})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.reason == Reason.ERROR
    assert resolution_details.error_code == error_code


def test_flag_metadata_includes_the_variation_index(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'FALLTHROUGH'})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {'variationIndex': 1}


def test_flag_metadata_omits_the_variation_index_for_default_values(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, None, {'kind': 'ERROR', 'errorKind': 'FLAG_NOT_FOUND'})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {}


def test_flag_metadata_includes_in_experiment_for_experiment_evaluations(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'FALLTHROUGH', 'inExperiment': True})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {'variationIndex': 1, 'inExperiment': True}


def test_flag_metadata_omits_in_experiment_for_non_experiment_evaluations(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'FALLTHROUGH', 'inExperiment': False})
    resolution_details = details_converter.to_resolution_details(detail)
    assert 'inExperiment' not in resolution_details.flag_metadata


def test_flag_metadata_includes_the_rule_for_rule_matches(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'RULE_MATCH', 'ruleIndex': 2, 'ruleId': 'the-rule-id'})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {'variationIndex': 1, 'ruleIndex': 2, 'ruleId': 'the-rule-id'}


def test_flag_metadata_includes_the_prerequisite_key(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'PREREQUISITE_FAILED', 'prerequisiteKey': 'the-prerequisite-key'})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {'variationIndex': 1, 'prerequisiteKey': 'the-prerequisite-key'}


def test_flag_metadata_includes_the_big_segments_status(details_converter: ResolutionDetailsConverter):
    detail = EvaluationDetail(True, 1, {'kind': 'FALLTHROUGH', 'bigSegmentsStatus': 'STALE'})
    resolution_details = details_converter.to_resolution_details(detail)
    assert resolution_details.flag_metadata == {'variationIndex': 1, 'bigSegmentsStatus': 'STALE'}
