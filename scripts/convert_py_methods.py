#!/usr/bin/env python3
"""
Convert py_methods.json to batch upload format
Flattens built_in_functions array into domain/terms structure
"""
import json

# Read source file
with open('.kiro/specs/tutor-system/py_methods.json', 'r') as f:
    data = json.load(f)

# Convert to batch upload format
batch_data = {
    "domains": [
        {
            "node_type": "domain",
            "data": {
                "name": "Python Built-in Functions",
                "description": "Comprehensive collection of Python's built-in functions that are always available without importing any module",
                "subject": "python",
                "difficulty": "intermediate",
                "estimated_hours": 20,
                "prerequisites": ["Python basics", "Functions"]
            },
            "metadata": {
                "version": 1,
                "tags": ["python", "built-in", "functions", "standard-library"],
                "source": "py_methods.json"
            },
            "terms": []
        }
    ]
}

# Convert each function to a term
for func in data['built_in_functions']:
    # Build definition from description
    definition = func['description'].strip()
    
    # Add notes if present
    if func.get('notes'):
        definition += "\n\nNotes:\n" + "\n".join(f"- {note}" for note in func['notes'])
    
    # Ensure definition is at least 10 characters
    if len(definition) < 10:
        definition = f"Python built-in function: {func['name']}"
    
    term = {
        "node_type": "term",
        "data": {
            "term": func['name'],
            "definition": definition,
            "difficulty": "intermediate",
            "module": "built-in"
        },
        "metadata": {
            "signature": func.get('signature', ''),
            "has_examples": len(func.get('examples', [])) > 0
        }
    }
    
    # Add signature to definition if present
    if func.get('signature'):
        term['data']['code_example'] = func['signature']
    
    # Add examples if present
    if func.get('examples'):
        term['data']['examples'] = func['examples'][:3]  # Limit to 3 examples
    
    batch_data['domains'][0]['terms'].append(term)

# Write output file
with open('python_builtin_functions_upload.json', 'w') as f:
    json.dump(batch_data, f, indent=2)

print(f"✅ Converted {len(batch_data['domains'][0]['terms'])} functions")
print(f"📄 Output: python_builtin_functions_upload.json")
