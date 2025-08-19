#!/usr/bin/env python3
"""
OSCAL Controls Explorer
A simple utility to explore and search security controls
"""
import json
import sys
import os
import argparse
import re

def load_controls(file_path):
    """Load controls from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading controls file: {e}")
        return {}


def load_default_controls():
    """Load controls from the default security_controls.json file"""
    import os
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security_controls.json")
    return load_controls(default_path)

def search_controls(controls, search_term, search_field=None, case_sensitive=False):
    """Search controls by term in specified field"""
    results = {}
    
    # Create regex pattern
    if case_sensitive:
        pattern = re.compile(search_term)
    else:
        pattern = re.compile(search_term, re.IGNORECASE)
    
    for control_id, control in controls.items():
        # If searching by ID
        if search_field == 'id' and pattern.search(control_id):
            results[control_id] = control
            continue
            
        # If search_field is specified, only search in that field
        if search_field and search_field in control:
            if pattern.search(str(control[search_field])):
                results[control_id] = control
        # Otherwise, search in all fields
        elif not search_field:
            for field, value in control.items():
                if pattern.search(str(value)):
                    results[control_id] = control
                    break
    
    return results

def list_controls(controls, family=None, limit=None):
    """List controls, optionally filtered by family"""
    results = {}
    
    if family:
        for control_id, control in controls.items():
            if control_id.lower().startswith(family.lower()):
                results[control_id] = control
    else:
        results = controls
    
    # Sort by ID
    sorted_ids = sorted(results.keys())
    
    if limit:
        sorted_ids = sorted_ids[:limit]
    
    return {control_id: results[control_id] for control_id in sorted_ids}

def print_control(control_id, control, detail_level=1):
    """Print control information with specified detail level"""
    print(f"\n--- {control_id} ---")
    print(f"Title: {control.get('title', 'N/A')}")
    
    if detail_level > 1:
        print(f"Category: {control.get('category', 'N/A')}")
        print(f"Criticality: {control.get('criticality', 'N/A')}")
    
    if detail_level > 2:
        print("\nDescription:")
        description = control.get('description', 'No description available')
        # Wrap description text
        for i in range(0, len(description), 80):
            print(description[i:i+80])
    
    print("-" * (len(control_id) + 8))

def find_relevant_controls_for_smart_contract(contract_text, num_results=10):
    """Find controls relevant to a given smart contract text using semantic matching"""
    controls = load_default_controls()
    
    # Keywords to search for in smart contract text related to security
    keywords = [
        "access control", "authentication", "authorization", "confidentiality", "integrity",
        "availability", "audit", "logging", "monitoring", "encryption", "key management",
        "secure communication", "input validation", "output encoding", "error handling",
        "session management", "configuration", "secure defaults", "sensitive data", "privacy",
        "verification", "validation", "compliance", "digital signature", "hash", "cryptography",
        "certificate", "credential", "identity", "role", "privilege", "permission", "asset",
        "supply chain", "third party", "vendor", "component", "library", "dependency",
        "vulnerability", "patch", "update", "baseline", "hardening", "secure coding",
        "least privilege", "separation of duties", "defense in depth", "security testing",
        "penetration testing", "code review", "security assessment", "risk assessment",
        "threat modeling", "incident response", "disaster recovery", "business continuity",
        "backup", "restore", "physical security", "personnel security", "training", "awareness"
    ]
    
    # Score controls based on keyword matches in contract text
    control_scores = {}
    contract_text_lower = contract_text.lower()
    
    # Find explicit control mentions
    control_pattern = re.compile(r'([a-z]{2})[-.]([0-9]+)(?:[.]([0-9]+))?', re.IGNORECASE)
    explicit_controls = control_pattern.findall(contract_text_lower)
    explicit_control_ids = set()
    
    for family, number, subnumber in explicit_controls:
        if subnumber:
            control_id = f"{family.lower()}-{number}.{subnumber}"
        else:
            control_id = f"{family.lower()}-{number}"
        explicit_control_ids.add(control_id)
    
    # Prioritize explicitly mentioned controls
    for control_id, control in controls.items():
        if control_id.lower() in explicit_control_ids:
            control_scores[control_id] = 100  # Very high score for explicit mentions
            continue
            
        score = 0
        control_text = json.dumps(control).lower()
        
        # Check for keyword matches in both contract and control
        for keyword in keywords:
            if keyword in contract_text_lower and keyword in control_text:
                score += 5
        
        # Additional score for title match
        title = control.get("title", "").lower()
        for word in title.split():
            if word and len(word) > 3 and word in contract_text_lower:
                score += 3
        
        # Score based on control family relevance
        # Focus on controls in supply chain, cryptography, integrity families
        if control_id.startswith("sr-"):
            score += 10  # Supply chain is highly relevant
        elif control_id.startswith("sc-") or control_id.startswith("si-"):
            score += 5   # System/communications protection and system integrity
        elif control_id.startswith("ia-") or control_id.startswith("ac-"):
            score += 3   # Identity/authentication and access control
        
        if score > 0:
            control_scores[control_id] = score
    
    # Sort controls by score and return top N
    sorted_controls = sorted(control_scores.items(), key=lambda x: x[1], reverse=True)[:num_results]
    return [(control_id, controls[control_id], score) for control_id, score in sorted_controls]


def main():
    parser = argparse.ArgumentParser(description='Explore and search security controls')
    parser.add_argument('--file', default='security_controls.json', 
                        help='Path to security controls JSON file')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search controls')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--field', help='Specific field to search in')
    search_parser.add_argument('--case-sensitive', action='store_true', help='Case sensitive search')
    search_parser.add_argument('--detail', type=int, default=2, choices=[1, 2, 3], 
                              help='Detail level: 1=minimal, 2=standard, 3=full')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List controls')
    list_parser.add_argument('--family', help='Filter by control family (e.g., ac, ia, cm)')
    list_parser.add_argument('--limit', type=int, help='Limit number of results')
    list_parser.add_argument('--detail', type=int, default=1, choices=[1, 2, 3], 
                            help='Detail level: 1=minimal, 2=standard, 3=full')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get specific control by ID')
    get_parser.add_argument('control_id', help='Control ID')
    get_parser.add_argument('--detail', type=int, default=3, choices=[1, 2, 3], 
                           help='Detail level: 1=minimal, 2=standard, 3=full')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show control statistics')
    
    # Smart contract analysis command
    sc_parser = subparsers.add_parser('analyze', help='Find controls relevant to a smart contract')
    sc_parser.add_argument('contract_file', help='Path to smart contract file')
    sc_parser.add_argument('--limit', type=int, default=10, help='Limit number of results')
    
    args = parser.parse_args()
    
    # Load controls from file
    controls_file = args.file
    if not os.path.exists(controls_file):
        print(f"Error: File not found: {controls_file}")
        return 1
    
    controls = load_controls(controls_file)
    if not controls:
        print("No controls found in file")
        return 1
    
    # Execute command
    if args.command == 'search':
        results = search_controls(controls, args.term, args.field, args.case_sensitive)
        print(f"Found {len(results)} matching controls:")
        for control_id, control in results.items():
            print_control(control_id, control, args.detail)
    
    elif args.command == 'list':
        results = list_controls(controls, args.family, args.limit)
        print(f"Listing {len(results)} controls:")
        for control_id, control in results.items():
            print_control(control_id, control, args.detail)
    
    elif args.command == 'get':
        if args.control_id in controls:
            print_control(args.control_id, controls[args.control_id], args.detail)
        else:
            print(f"Control not found: {args.control_id}")
            return 1
    
    elif args.command == 'stats':
        # Get control families and count
        families = {}
        for control_id in controls:
            family = control_id.split('-')[0].lower() if '-' in control_id else 'other'
            if family not in families:
                families[family] = 0
            families[family] += 1
        
        print(f"Total controls: {len(controls)}")
        print("\nControl families:")
        for family, count in sorted(families.items(), key=lambda x: x[1], reverse=True):
            print(f"  {family.upper()}: {count} controls")
            
    elif args.command == 'analyze':
        # Read the smart contract file
        try:
            with open(args.contract_file, 'r') as f:
                contract_text = f.read()
        except Exception as e:
            print(f"Error reading contract file: {e}")
            return 1
            
        # Find relevant controls
        print(f"Analyzing smart contract: {args.contract_file}")
        relevant_controls = find_relevant_controls_for_smart_contract(contract_text, args.limit)
        
        print(f"Found {len(relevant_controls)} relevant controls:")
        for control_id, control, score in relevant_controls:
            print(f"\n--- {control_id} (Relevance Score: {score}) ---")
            print(f"Title: {control.get('title', 'N/A')}")
            print(f"Category: {control.get('category', 'N/A')}")
            print(f"Criticality: {control.get('criticality', 'N/A')}")
            
            description = control.get('description', 'No description available')
            print("\nDescription:")
            for i in range(0, len(description), 80):
                print(description[i:i+80])
            print("-" * (len(control_id) + 22))
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
