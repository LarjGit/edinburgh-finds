import os

def test_notes_analysis_exists():
    file_path = "conductor/tracks/architecture_docs_20260114/notes.md"
    with open(file_path, 'r') as f:
        content = f.read()
    
    assert "## Codebase Analysis" in content, "Missing 'Codebase Analysis' section in notes.md"
    assert "Schema Consistency" in content, "Missing schema analysis"
    assert "BaseConnector" in content, "Missing ingestion analysis"

if __name__ == "__main__":
    try:
        test_notes_analysis_exists()
        print("Test Passed: Analysis present.")
    except AssertionError as e:
        print(f"Test Failed: {e}")
        exit(1)
