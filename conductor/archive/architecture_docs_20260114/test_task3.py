import os

def test_notes_c4_exists():
    file_path = "conductor/tracks/architecture_docs_20260114/notes.md"
    with open(file_path, 'r') as f:
        content = f.read()
    
    assert "## C4 Diagrams Analysis" in content, "Missing 'C4 Diagrams Analysis' section"
    assert "Level 1" in content, "Missing Level 1 analysis"
    assert "Level 3" in content, "Missing Level 3 analysis"

if __name__ == "__main__":
    try:
        test_notes_c4_exists()
        print("Test Passed: C4 Analysis present.")
    except AssertionError as e:
        print(f"Test Failed: {e}")
        exit(1)
