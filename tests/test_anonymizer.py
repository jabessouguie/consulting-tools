import pytest
from utils.anonymizer import PIIAnonymizer

@pytest.fixture
def anonymizer():
    return PIIAnonymizer()

def test_mask_email(anonymizer):
    text = "Contactez-moi à jean.dupont@gmail.com pour plus d'infos."
    masked = anonymizer.mask(text)
    assert "[EMAIL]" in masked
    assert "jean.dupont@gmail.com" not in masked

def test_mask_phone(anonymizer):
    text = "Mon numéro est le 06 12 34 56 78 ou +33 1 23 45 67 89."
    masked = anonymizer.mask(text)
    assert "[PHONE]" in masked
    assert "06 12 34 56 78" not in masked
    assert "+33 1 23 45 67 89" not in masked

def test_mask_name(anonymizer):
    text = "M. Jean Dupont et Mme Marie Curie ont participé."
    masked = anonymizer.mask(text)
    assert "[NAME]" in masked
    assert "Jean Dupont" not in masked
    assert "Marie Curie" not in masked

def test_mask_address(anonymizer):
    text = "Rendez-vous au 123 rue de la Paix, 75002 PARIS."
    masked = anonymizer.mask(text)
    assert "[ADDRESS]" in masked
    assert "123 rue de la Paix" not in masked

def test_no_pii(anonymizer):
    text = "Ceci est un texte sans données personnelles."
    masked = anonymizer.mask(text)
    assert masked == text

def test_multiple_pii(anonymizer):
    text = "M. Jean Dupont (jean.dupont@example.com) au 123 rue de la Paix."
    masked = anonymizer.mask(text)
    assert "[NAME]" in masked
    assert "[EMAIL]" in masked
    assert "[ADDRESS]" in masked

def test_mask_empty_string_returns_empty(anonymizer):
    # line 29: return text when not text
    assert anonymizer.mask("") == ""

def test_mask_none_returns_none(anonymizer):
    # line 29: return text when not text
    assert anonymizer.mask(None) is None

def test_custom_mask_applied():
    # lines 35-36: custom mask substitution
    anon = PIIAnonymizer(custom_masks=["Accenture", "McKinsey"])
    text = "Je travaille chez Accenture et McKinsey est notre concurrent."
    masked = anon.mask(text)
    assert "[FILTERED_ENTITY]" in masked
    assert "Accenture" not in masked
    assert "McKinsey" not in masked

def test_empty_string_in_custom_masks_skipped():
    # line 35: if custom: skips empty strings
    anon = PIIAnonymizer(custom_masks=["", "ValidName"])
    text = "Rencontre avec ValidName aujourd'hui."
    masked = anon.mask(text)
    assert "[FILTERED_ENTITY]" in masked
