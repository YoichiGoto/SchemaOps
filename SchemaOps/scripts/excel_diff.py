#!/usr/bin/env python3
"""
Excel/CSV schema diff analyzer for retailer format changes.
Compares old and new templates to identify structural changes.
"""
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

def read_csv_structure(file_path: Path) -> Dict[str, Any]:
    """Read CSV file and extract structural information."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        
        # Sample a few rows to understand data types and constraints
        sample_rows = []
        for i, row in enumerate(reader):
            if i >= 5:  # Sample first 5 rows
                break
            sample_rows.append(row)
    
    # Analyze column characteristics
    columns = {}
    for header in headers:
        columns[header] = {
            'name': header,
            'required': False,  # Would need business logic to determine
            'dataType': 'string',  # Default assumption
            'maxLength': None,
            'allowedValues': None,
            'examples': []
        }
        
        # Analyze sample data
        for row in sample_rows:
            if header in row and row[header]:
                value = row[header]
                columns[header]['examples'].append(value)
                
                # Infer data type
                if value.isdigit():
                    columns[header]['dataType'] = 'integer'
                elif value.replace('.', '').isdigit():
                    columns[header]['dataType'] = 'decimal'
                elif len(value) > 50:
                    columns[header]['maxLength'] = len(value)
    
    return {
        'headers': headers,
        'columns': columns,
        'rowCount': len(sample_rows),
        'filePath': str(file_path)
    }

def compare_structures(old_structure: Dict[str, Any], new_structure: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two CSV structures and identify differences."""
    old_headers = set(old_structure['headers'])
    new_headers = set(new_structure['headers'])
    
    added_columns = list(new_headers - old_headers)
    removed_columns = list(old_headers - new_headers)
    common_columns = list(old_headers & new_headers)
    
    # Analyze changes in common columns
    column_changes = []
    for col in common_columns:
        old_col = old_structure['columns'][col]
        new_col = new_structure['columns'][col]
        
        changes = []
        
        # Check data type changes
        if old_col['dataType'] != new_col['dataType']:
            changes.append({
                'type': 'dataType',
                'old': old_col['dataType'],
                'new': new_col['dataType']
            })
        
        # Check length changes
        if old_col['maxLength'] != new_col['maxLength']:
            changes.append({
                'type': 'maxLength',
                'old': old_col['maxLength'],
                'new': new_col['maxLength']
            })
        
        # Check required status changes (would need business logic)
        if old_col['required'] != new_col['required']:
            changes.append({
                'type': 'required',
                'old': old_col['required'],
                'new': new_col['required']
            })
        
        if changes:
            column_changes.append({
                'column': col,
                'changes': changes
            })
    
    # Categorize changes by severity
    severity = 'minor'
    if added_columns or removed_columns:
        severity = 'major'
    if any(change['type'] == 'required' and change['new'] for change in 
           [c for col_changes in column_changes for c in col_changes['changes']]):
        severity = 'critical'
    
    return {
        'addedColumns': added_columns,
        'removedColumns': removed_columns,
        'columnChanges': column_changes,
        'severity': severity,
        'summary': f"Added: {len(added_columns)}, Removed: {len(removed_columns)}, Modified: {len(column_changes)}"
    }

def generate_change_log_entry(diff_result: Dict[str, Any], retailer_name: str) -> Dict[str, Any]:
    """Generate Change_Log entry from diff results."""
    from datetime import datetime
    
    change_summary = diff_result['summary']
    if diff_result['addedColumns']:
        change_summary += f" | New columns: {', '.join(diff_result['addedColumns'])}"
    if diff_result['removedColumns']:
        change_summary += f" | Removed columns: {', '.join(diff_result['removedColumns'])}"
    
    impacted_attrs = []
    for col_change in diff_result['columnChanges']:
        for change in col_change['changes']:
            if change['type'] == 'required' and change['new']:
                impacted_attrs.append(f"{col_change['column']}(now required)")
            elif change['type'] == 'dataType':
                impacted_attrs.append(f"{col_change['column']}(type: {change['old']}→{change['new']})")
    
    # Set SLA based on severity
    sla_hours = {'critical': 72, 'major': 120, 'minor': 336}[diff_result['severity']]
    
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'target': 'retailer',
        'name': f'{retailer_name} Vendor Spec',
        'changeSummary': change_summary,
        'impactedAttributes': ', '.join(impacted_attrs) if impacted_attrs else 'None',
        'severity': diff_result['severity'],
        'SLA_hours': sla_hours,
        'ETA': (datetime.now().timestamp() + sla_hours * 3600),
        'status': 'new',
        'owner': 'ops',
        'lastVerifiedAt': datetime.now().strftime('%Y-%m-%d'),
        'docURL': '',
        'sourceURL': f'file://{retailer_name}/spec.xlsx',
        'notes': f'Automated diff analysis: {len(diff_result["columnChanges"])} columns modified'
    }

def main():
    if len(sys.argv) < 4:
        print("Usage: excel_diff.py <old_file.csv> <new_file.csv> [retailer_name]")
        sys.exit(1)
    
    old_file = Path(sys.argv[1])
    new_file = Path(sys.argv[2])
    retailer_name = sys.argv[3] if len(sys.argv) > 3 else 'Unknown'
    
    if not old_file.exists() or not new_file.exists():
        print("Error: Input files do not exist")
        sys.exit(1)
    
    # Read structures
    print(f"Analyzing {old_file}...")
    old_structure = read_csv_structure(old_file)
    
    print(f"Analyzing {new_file}...")
    new_structure = read_csv_structure(new_file)
    
    # Compare structures
    print("Comparing structures...")
    diff_result = compare_structures(old_structure, new_structure)
    
    # Generate change log entry
    change_log_entry = generate_change_log_entry(diff_result, retailer_name)
    
    # Output results
    print("\n=== DIFF ANALYSIS RESULTS ===")
    print(f"Severity: {diff_result['severity']}")
    print(f"Summary: {diff_result['summary']}")
    
    if diff_result['addedColumns']:
        print(f"\nAdded columns: {', '.join(diff_result['addedColumns'])}")
    
    if diff_result['removedColumns']:
        print(f"Removed columns: {', '.join(diff_result['removedColumns'])}")
    
    if diff_result['columnChanges']:
        print("\nColumn changes:")
        for col_change in diff_result['columnChanges']:
            print(f"  {col_change['column']}:")
            for change in col_change['changes']:
                print(f"    {change['type']}: {change['old']} → {change['new']}")
    
    # Save change log entry
    output_file = Path(f"change_log_{retailer_name}_{datetime.now().strftime('%Y%m%d')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(change_log_entry, f, ensure_ascii=False, indent=2)
    
    print(f"\nChange log entry saved to: {output_file}")
    print(f"SLA: {change_log_entry['SLA_hours']} hours")

if __name__ == '__main__':
    from datetime import datetime
    main()