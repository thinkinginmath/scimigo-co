import pytest

from co.services.evaluators.meta_signal_extractor import MetaSignalExtractor


def test_extract_correctness_signals():
    extractor = MetaSignalExtractor()
    test_results = {
        "visible_passed": 3,
        "visible_total": 4,
        "hidden_passed": 8,
        "hidden_total": 10,
        "categories": ["edge_cases"],
    }

    signals = extractor._extract_correctness_signals(test_results)
    assert signals["visible_pass_rate"] == 0.75
    assert signals["hidden_pass_rate"] == 0.8
    assert "edge_cases" in signals["categories_failed"]


def test_complexity_analysis_nested_loops():
    code = """
    def solution(arr):
        for i in range(len(arr)):
            for j in range(len(arr)):
                for k in range(len(arr)):
                    process(arr[i], arr[j], arr[k])
    """
    extractor = MetaSignalExtractor()
    signals = extractor._analyze_python_complexity(code)
    assert signals["estimated_time"] == "O(n^3)"
    assert signals["loop_depth"] == 3
