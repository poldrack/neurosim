import pytest
from pathlib import Path


@pytest.fixture
def sample_taxonomy(tmp_path):
    """Create a minimal disorder taxonomy JSON file for testing."""
    import json

    data = {
        "title": "Test Taxonomy",
        "categories": [
            {
                "category": "Test Category",
                "description": "A test category",
                "disorders": [
                    {
                        "name": "Test Disorder",
                        "symptoms": "Patient shows test symptoms.",
                        "brain_region": "Test region of the brain.",
                        "how_to_test": "Administer test protocol."
                    },
                    {
                        "name": "Another Disorder",
                        "symptoms": "Different symptoms here.",
                        "brain_region": "Different brain region.",
                        "how_to_test": "Different testing approach."
                    }
                ]
            },
            {
                "category": "Second Category",
                "description": "Another category",
                "disorders": [
                    {
                        "name": "Third Disorder",
                        "symptoms": "Third set of symptoms.",
                        "brain_region": "Third brain region.",
                        "how_to_test": "Third test protocol."
                    }
                ]
            }
        ]
    }
    filepath = tmp_path / "taxonomy.json"
    filepath.write_text(json.dumps(data))
    return filepath


def test_load_disorders_returns_flat_list(sample_taxonomy):
    from neurosim.disorders import load_disorders

    disorders = load_disorders(sample_taxonomy)
    assert len(disorders) == 3
    assert all(isinstance(d, dict) for d in disorders)


def test_load_disorders_each_has_required_fields(sample_taxonomy):
    from neurosim.disorders import load_disorders

    disorders = load_disorders(sample_taxonomy)
    required_fields = {"name", "symptoms", "brain_region", "how_to_test", "category"}
    for d in disorders:
        assert required_fields.issubset(d.keys()), f"Missing fields in {d['name']}"


def test_load_disorders_category_attached(sample_taxonomy):
    from neurosim.disorders import load_disorders

    disorders = load_disorders(sample_taxonomy)
    names_to_categories = {d["name"]: d["category"] for d in disorders}
    assert names_to_categories["Test Disorder"] == "Test Category"
    assert names_to_categories["Third Disorder"] == "Second Category"


def test_get_random_disorder(sample_taxonomy):
    from neurosim.disorders import load_disorders, get_random_disorder

    disorders = load_disorders(sample_taxonomy)
    disorder = get_random_disorder(disorders)
    assert disorder["name"] in {"Test Disorder", "Another Disorder", "Third Disorder"}


def test_load_disorders_file_not_found():
    from neurosim.disorders import load_disorders

    with pytest.raises(FileNotFoundError):
        load_disorders(Path("/nonexistent/path.json"))
