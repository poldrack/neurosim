import pytest


@pytest.fixture
def sample_disorder():
    return {
        "name": "Hemispatial Neglect",
        "symptoms": "A failure to report, respond to, or orient toward stimuli on the side of space opposite a brain lesion.",
        "brain_region": "Right posterior parietal lobe.",
        "how_to_test": "Line bisection test: ask the patient to mark the center of a horizontal line.",
        "category": "Disorders of Attention"
    }


def test_build_patient_prompt_contains_symptoms(sample_disorder):
    from neurosim.prompts import build_patient_prompt

    prompt = build_patient_prompt(sample_disorder)
    assert "NEVER use medical or clinical terminology" in prompt
    assert "NEVER name your condition" in prompt


def test_build_patient_prompt_contains_disorder_info(sample_disorder):
    from neurosim.prompts import build_patient_prompt

    prompt = build_patient_prompt(sample_disorder)
    assert "YOUR SYMPTOMS AND EXPERIENCES" in prompt
    assert "HOW YOU RESPOND TO CLINICAL TESTS" in prompt
    assert sample_disorder["symptoms"] in prompt
    assert sample_disorder["how_to_test"] in prompt


def test_build_patient_prompt_does_not_contain_disorder_name(sample_disorder):
    from neurosim.prompts import build_patient_prompt

    prompt = build_patient_prompt(sample_disorder)
    assert "Hemispatial Neglect" not in prompt
    assert "hemispatial neglect" not in prompt.lower()


def test_build_clinician_prompt_has_no_disorder_info(sample_disorder):
    from neurosim.prompts import build_clinician_prompt

    prompt = build_clinician_prompt()
    assert "Hemispatial" not in prompt
    assert "[DIAGNOSIS:" in prompt


def test_build_clinician_prompt_contains_instructions():
    from neurosim.prompts import build_clinician_prompt

    prompt = build_clinician_prompt()
    assert "clinical neurologist" in prompt.lower() or "neurologist" in prompt.lower()
    assert "[DIAGNOSIS:" in prompt
    assert "no prior information" in prompt.lower()
