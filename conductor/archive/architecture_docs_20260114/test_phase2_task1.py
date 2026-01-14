import os

def test_architecture_created():
    file_path = "ARCHITECTURE.md"
    assert os.path.exists(file_path), "ARCHITECTURE.md does not exist"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "# Architecture: Edinburgh Finds" in content
    assert "## 1. System Overview" in content
    assert "## 6. Key Technical Decisions" in content
    assert "Next.js" in content
    assert "Python" in content
    assert "Supabase" in content

if __name__ == "__main__":
    try:
        test_architecture_created()
        print("Test Passed: ARCHITECTURE.md basic structure exists.")
    except Exception as e:
        print(f"Test Failed: {e}")
        exit(1)
