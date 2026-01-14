import os

def test_ingestion_section_exists():
    file_path = "ARCHITECTURE.md"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "## 3. Data Ingestion & Pipeline Architecture" in content
    assert "Autonomous Ingestion" in content
    assert "RawIngestion" in content
    assert "Connectors" in content
    assert "Deduplication" in content

if __name__ == "__main__":
    try:
        test_ingestion_section_exists()
        print("Test Passed: Ingestion section exists.")
    except Exception as e:
        print(f"Test Failed: {e}")
        exit(1)
