import os

def test_uef_section_exists():
    file_path = "ARCHITECTURE.md"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "## 2. Universal Entity Framework" in content
    assert "## 6. Key Technical Decisions" in content # Ensure we didn't overwrite
    
    # Check for pillars
    assert "**Infrastructure:** Physical locations" in content
    assert "**Commerce:** Retailers" in content
    assert "**Guidance:** Human expertise" in content
    
    # Check for schema concepts
    assert "Generic Attributes" not in content # I used "Flexible Attribute Bucket"
    assert "Flexible Attribute Bucket" in content

if __name__ == "__main__":
    try:
        test_uef_section_exists()
        print("Test Passed: UEF section exists.")
    except Exception as e:
        print(f"Test Failed: {e}")
        exit(1)
