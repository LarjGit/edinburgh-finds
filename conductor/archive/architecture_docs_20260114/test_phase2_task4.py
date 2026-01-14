import os

def test_trust_section_exists():
    file_path = "ARCHITECTURE.md"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "## 4. Confidence Grading & Trust Architecture" in content
    assert "Business Claimed" in content
    assert "Conflict Resolution" in content
    assert "field_confidence" in content

if __name__ == "__main__":
    try:
        test_trust_section_exists()
        print("Test Passed: Trust section exists.")
    except Exception as e:
        print(f"Test Failed: {e}")
        exit(1)
