import argparse
import os
import orjson
from collections import defaultdict, deque
from pathlib import Path

def find_json_files(path: Path) -> list[Path]:
    """Find all .json and .jsonl files in a given path."""
    if path.is_file():
        if path.suffix in ['.json', '.jsonl']:
            return [path]
        return []
    elif path.is_dir():
        return list(path.rglob('*.json')) + list(path.rglob('*.jsonl'))
    return []

def process_json_object(data, all_unique_keys, field_values):
    """
    Efficiently processes a single JSON object (from a file or a line)
    to populate unique keys and field values. Traverses the object only once
    using an iterative breadth-first approach.
    """
    queue = deque([(data, "")])

    while queue:
        current_obj, parent_key = queue.popleft()

        if isinstance(current_obj, dict):
            for k, v in current_obj.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                all_unique_keys.add(new_key)
                
                if isinstance(v, dict) or isinstance(v, list):
                    queue.append((v, new_key))
                else:
                    field_values[new_key].add(v)
        
        elif isinstance(current_obj, list):
            # Check if it's a list of objects or a list of simple values
            is_simple_list = True
            for item in current_obj:
                if isinstance(item, (dict, list)):
                    is_simple_list = False
                    # The parent_key for items in a list is the key of the list itself
                    queue.append((item, parent_key))
            
            # If it's a list of simple values (e.g., strings, numbers), add them
            if is_simple_list and parent_key:
                for simple_value in current_obj:
                    field_values[parent_key].add(simple_value)

def main():
    parser = argparse.ArgumentParser(description="Analyze JSON files to extract unique keys and their values.")
    parser.add_argument("input_path", type=str, help="Path to a JSON/JSONL file or a directory containing them.")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory to save the analysis results.")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)

    run_output_dir = output_dir / f"analysis_{input_path.name.replace('/', '_')}_{os.urandom(4).hex()}"
    field_values_dir = run_output_dir / "field_values"
    field_values_dir.mkdir(parents=True, exist_ok=True)

    json_files = find_json_files(input_path)
    if not json_files:
        print(f"No JSON or JSONL files found in '{input_path}'.")
        return

    all_unique_keys = set()
    field_values = defaultdict(set)

    print(f"Found {len(json_files)} files to process.")

    for file_path in json_files:
        print(f"Processing {file_path}...")
        with file_path.open('rb') as f:
            if file_path.suffix == '.jsonl':
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = orjson.loads(line)
                        process_json_object(data, all_unique_keys, field_values)
                    except orjson.JSONDecodeError:
                        print(f"  - Warning: Could not decode line in {file_path}")
            else: # .json
                try:
                    content = f.read()
                    if not content.strip():
                        print(f"  - Warning: Empty JSON file {file_path}")
                        continue
                    data = orjson.loads(content)
                    process_json_object(data, all_unique_keys, field_values)
                except orjson.JSONDecodeError:
                    print(f"  - Warning: Could not decode JSON from {file_path}")

    # Save unique keys
    unique_keys_path = run_output_dir / "unique_fields.txt"
    with unique_keys_path.open('w', encoding='utf-8') as f:
        for key in sorted(list(all_unique_keys)):
            f.write(f"{key}\n")
    print(f"\nSaved {len(all_unique_keys)} unique fields to '{unique_keys_path}'")

    # Save unique values for each field
    print(f"Saving unique values for {len(field_values)} fields...")
    for field, values in field_values.items():
        safe_filename = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in field)
        field_values_path = field_values_dir / f"{safe_filename}.txt"
        with field_values_path.open('w', encoding='utf-8') as f:
            # Sort values to ensure consistent output, handle different types
            try:
                sorted_values = sorted(list(values))
            except TypeError:
                # Handle mixtures of types (e.g., numbers and strings) by converting to string
                sorted_values = sorted([str(v) for v in values])

            for value in sorted_values:
                # Handle complex objects that might have been added as values
                if isinstance(value, (list, dict)):
                    value = orjson.dumps(value).decode('utf-8')
                f.write(f"{str(value)}\n")
    
    print(f"Saved field values in '{field_values_dir}'")
    print(f"Analysis complete. Results are in: {run_output_dir}")

if __name__ == "__main__":
    main()