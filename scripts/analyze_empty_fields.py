#!/usr/bin/env python3
"""
Analyze data.json to identify fields that are always empty, null, or have constant values.
"""

import json
from collections import defaultdict
from typing import Dict, List, Any, Set

def analyze_empty_fields(data_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Analyze JSON data to find fields that are always empty, null, or constant.
    
    Returns a dictionary with field analysis:
    - always_empty: fields that are always empty strings
    - always_null: fields that are always None/null
    - always_same: fields that always have the same non-empty value
    - mixed: fields that have different values
    """
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list) or len(data) == 0:
        print("Data should be a non-empty list")
        return {}
    
    # Initialize tracking dictionaries
    field_values = defaultdict(set)
    field_counts = defaultdict(int)
    empty_counts = defaultdict(int)
    null_counts = defaultdict(int)
    
    total_records = len(data)
    
    # Analyze each record
    for record in data:
        if not isinstance(record, dict):
            continue
            
        for field, value in record.items():
            field_counts[field] += 1
            
            if value is None:
                null_counts[field] += 1
                field_values[field].add("__NULL__")
            elif value == "":
                empty_counts[field] += 1
                field_values[field].add("__EMPTY__")
            elif isinstance(value, (list, dict)) and len(value) == 0:
                empty_counts[field] += 1
                field_values[field].add("__EMPTY_COLLECTION__")
            else:
                # Store actual value (convert lists/dicts to string for comparison)
                if isinstance(value, (list, dict)):
                    field_values[field].add(json.dumps(value, sort_keys=True))
                else:
                    field_values[field].add(str(value))
    
    # Categorize fields
    results = {
        "always_empty": [],
        "always_null": [],
        "always_same": [],
        "single_unique": [],
        "few_unique": [],
        "mostly_empty": [],
        "mixed": []
    }
    
    for field in field_counts:
        count = field_counts[field]
        values = field_values[field]
        empty_count = empty_counts[field]
        null_count = null_counts[field]
        
        # Calculate percentages
        empty_pct = (empty_count / count * 100) if count > 0 else 0
        null_pct = (null_count / count * 100) if count > 0 else 0
        
        if count == total_records:  # Field appears in all records
            if empty_count == count:
                results["always_empty"].append({
                    "field": field,
                    "occurrences": count
                })
            elif null_count == count:
                results["always_null"].append({
                    "field": field,
                    "occurrences": count
                })
            elif len(values) == 1 and "__EMPTY__" not in values and "__NULL__" not in values:
                # Always has the same non-empty value
                value = list(values)[0]
                if value == "__EMPTY_COLLECTION__":
                    results["always_empty"].append({
                        "field": field,
                        "occurrences": count,
                        "type": "empty_collection"
                    })
                else:
                    results["always_same"].append({
                        "field": field,
                        "value": value,
                        "occurrences": count
                    })
            elif len(values) <= 1:
                # 0 or 1 unique values (including null/empty)
                unique_values = [v for v in values if v not in ("__NULL__", "__EMPTY__", "__EMPTY_COLLECTION__")]
                results["single_unique"].append({
                    "field": field,
                    "unique_count": len(unique_values),
                    "values": list(unique_values)[:20] if unique_values else [],
                    "empty_percentage": empty_pct,
                    "null_percentage": null_pct
                })
            elif len(values) <= 3:
                # 2-3 unique values
                unique_values = [v for v in values if v not in ("__NULL__", "__EMPTY__", "__EMPTY_COLLECTION__")]
                truncated_values = [v[:20] + "..." if len(v) > 20 else v for v in unique_values]
                results["few_unique"].append({
                    "field": field,
                    "unique_count": len(unique_values),
                    "values": truncated_values,
                    "empty_percentage": empty_pct,
                    "null_percentage": null_pct
                })
            elif empty_pct > 90 or null_pct > 90:
                results["mostly_empty"].append({
                    "field": field,
                    "empty_percentage": empty_pct,
                    "null_percentage": null_pct,
                    "total_occurrences": count
                })
            else:
                results["mixed"].append({
                    "field": field,
                    "unique_values": len(values),
                    "empty_percentage": empty_pct,
                    "null_percentage": null_pct
                })
    
    return results

def print_analysis(results: Dict[str, List[Dict[str, Any]]]):
    """Pretty print the analysis results."""
    
    print("=" * 60)
    print("FIELD ANALYSIS REPORT")
    print("=" * 60)
    
    if results["always_empty"]:
        print("\n🚫 ALWAYS EMPTY (empty string or empty collection):")
        print("-" * 40)
        for item in results["always_empty"]:
            field_type = item.get("type", "empty_string")
            print(f"  • {item['field']} ({field_type})")
    
    if results["always_null"]:
        print("\n❌ ALWAYS NULL:")
        print("-" * 40)
        for item in results["always_null"]:
            print(f"  • {item['field']}")
    
    if results["always_same"]:
        print("\n🔒 ALWAYS SAME VALUE:")
        print("-" * 40)
        for item in results["always_same"]:
            value = item['value']
            if len(value) > 50:
                value = value[:50] + "..."
            print(f"  • {item['field']} = '{value}'")
    
    if results["single_unique"]:
        print("\n🔢 SINGLE UNIQUE VALUE (0-1 values):")
        print("-" * 40)
        for item in results["single_unique"]:
            values_str = ", ".join(item['values']) if item['values'] else "no non-null values"
            print(f"  • {item['field']}: {item['unique_count']} unique ({values_str})")
    
    if results["few_unique"]:
        print("\n🔤 FEW UNIQUE VALUES (2-3 values):")
        print("-" * 40)
        for item in results["few_unique"]:
            values_str = ", ".join(f"'{v}'" for v in item['values'])
            print(f"  • {item['field']}: {item['unique_count']} unique ({values_str})")
    
    if results["mostly_empty"]:
        print("\n⚠️  MOSTLY EMPTY (>90%):")
        print("-" * 40)
        for item in results["mostly_empty"]:
            print(f"  • {item['field']}: {item['empty_percentage']:.1f}% empty, {item['null_percentage']:.1f}% null")
    
    print("\n✅ FIELDS WITH VARIED DATA:")
    print("-" * 40)
    for item in results["mixed"]:
        print(f"  • {item['field']}: {item['unique_values']} unique values")

if __name__ == "__main__":
    import os
    
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "data.json")
    
    if not os.path.exists(data_path):
        print(f"Error: Could not find {data_path}")
        exit(1)
    
    print(f"Analyzing: {data_path}")
    results = analyze_empty_fields(data_path)
    print_analysis(results)
    
    # Save detailed results to JSON
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "field_analysis_report.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_path}")