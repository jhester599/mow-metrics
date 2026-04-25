from pathlib import Path


def test_requirements_include_runtime_dependencies():
    requirements = Path("requirements.txt").read_text()
    assert "streamlit" in requirements
    assert "gspread" in requirements
    assert "pytest" in requirements


def test_readme_documents_required_secrets_and_local_commands():
    readme = Path("README.md").read_text()
    assert "GOOGLE_SHEET_ID" in readme
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in readme
    assert "python -m pytest" in readme
    assert "streamlit run app.py" in readme
