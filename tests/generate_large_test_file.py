import json
import os
from faker import Faker

def generate_large_json(file_path: str, target_size_mb: int):
    """Generates a large JSON file for testing."""
    fake = Faker()
    target_size_bytes = target_size_mb * 1024 * 1024
    data = []
    
    print(f"Generating a large JSON file at '{file_path}' (target size: {target_size_mb}MB)...")

    # Create a directory for the file if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as f:
        f.write("[")
        is_first = True
        while os.path.getsize(file_path) < target_size_bytes:
            if not is_first:
                f.write(",")
            
            record = {
                "user_id": fake.uuid4(),
                "user_name": fake.name(),
                "email": fake.email(),
                "address": fake.address(),
                "company": fake.company(),
                "ip_address": fake.ipv4(),
                "notes": fake.paragraph(nb_sentences=5),
                "profile": fake.text(max_nb_chars=500),
                "historical_data": [
                    {
                        "timestamp": fake.iso8601(),
                        "event": "login",
                        "location": fake.city()
                    } for _ in range(3)
                ]
            }
            f.write(json.dumps(record, indent=2))
            is_first = False
        
        f.write("]")

    final_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"[*] Successfully generated '{file_path}' with a final size of {final_size:.2f}MB.")

if __name__ == "__main__":
    # Place the test file in a subdirectory to avoid cluttering the main tests folder
    output_file_path = "tests/test_data_pytest/large_test_file.json"
    generate_large_json(output_file_path, target_size_mb=150)
