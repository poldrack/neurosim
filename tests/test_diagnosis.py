import pytest


def test_exact_match_case_insensitive():
    from neurosim.diagnosis import check_diagnosis

    assert check_diagnosis("Broca's Aphasia", "broca's aphasia") is True
    assert check_diagnosis("Prosopagnosia", "PROSOPAGNOSIA") is True


def test_exact_match_wrong():
    from neurosim.diagnosis import check_diagnosis

    assert check_diagnosis("Broca's Aphasia", "Wernicke's Aphasia") is False


def test_fuzzy_match_partial():
    from neurosim.diagnosis import check_diagnosis

    assert check_diagnosis("Broca's Aphasia", "Broca's") is True
    assert check_diagnosis("Broca's Aphasia", "brocas aphasia") is True


def test_fuzzy_match_no_match():
    from neurosim.diagnosis import check_diagnosis

    assert check_diagnosis("Broca's Aphasia", "blindsight") is False


def test_extract_diagnosis_tag():
    from neurosim.diagnosis import extract_diagnosis_tag

    text = "Based on my evaluation, I believe you have [DIAGNOSIS: Prosopagnosia]. Let me explain."
    result = extract_diagnosis_tag(text)
    assert result == "Prosopagnosia"


def test_extract_diagnosis_tag_no_tag():
    from neurosim.diagnosis import extract_diagnosis_tag

    text = "I need to ask you a few more questions before I can make a determination."
    result = extract_diagnosis_tag(text)
    assert result is None


def test_extract_diagnosis_tag_strips_whitespace():
    from neurosim.diagnosis import extract_diagnosis_tag

    text = "You have [DIAGNOSIS:  Broca's Aphasia  ] based on your symptoms."
    result = extract_diagnosis_tag(text)
    assert result == "Broca's Aphasia"


def test_strip_diagnosis_tag_from_text():
    from neurosim.diagnosis import strip_diagnosis_tag

    text = "I believe you have [DIAGNOSIS: Prosopagnosia]. Let me explain why."
    result = strip_diagnosis_tag(text)
    assert result == "I believe you have Prosopagnosia. Let me explain why."


def test_build_llm_diagnosis_prompt():
    from neurosim.diagnosis import build_llm_diagnosis_prompt

    prompt = build_llm_diagnosis_prompt("Broca's Aphasia", "expressive aphasia")
    assert "Broca's Aphasia" in prompt
    assert "expressive aphasia" in prompt
