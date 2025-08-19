#!/usr/bin/env python3
"""
OSCAL Controls Processor
Extracts controls from NIST SP800-53 catalog in OSCAL format and converts them to our security controls format
"""
import json
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_controls(oscal_file):
    """Extract controls from OSCAL catalog and convert to our format"""
    logger.info(f"Processing OSCAL catalog file: {oscal_file}")
    
    try:
        with open(oscal_file, 'r') as f:
            oscal_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading OSCAL file: {e}")
        return {}
    
    # Our target format for controls
    controls = {}
    
    # Extract controls from the catalog
    if 'catalog' in oscal_data and 'groups' in oscal_data['catalog']:
        for group in oscal_data['catalog']['groups']:
            process_group(group, controls)
    
    logger.info(f"Extracted {len(controls)} controls")
    return controls

def process_group(group, controls, parent_id=""):
    """Process a control group and its controls/subgroups"""
    # Process controls in this group
    if 'controls' in group:
        for control in group['controls']:
            process_control(control, controls, parent_id)
    
    # Process subgroups if any
    if 'groups' in group:
        for subgroup in group['groups']:
            process_group(subgroup, controls, parent_id)

def process_control(control, controls, parent_id=""):
    """Process a single control and add it to our controls dictionary"""
    # Get control ID
    if 'id' not in control:
        return
    
    control_id = control['id']
    
    # Create control entry
    title = control.get('title', "")
    
    # Extract description
    description = ""
    if 'parts' in control:
        for part in control['parts']:
            if part.get('name') == 'statement':
                # Extract prose text from the statement
                if 'prose' in part:
                    description = part['prose']
                break
    
    # Determine criticality (default to medium)
    criticality = "medium"
    # Could implement logic to set criticality based on control attributes
    
    # Determine category (default to Security)
    category = "Security"
    if parent_id:
        # Could set category based on parent group
        pass
    
    # Add to controls dictionary
    controls[control_id] = {
        "id": control_id,
        "title": title,
        "description": description,
        "category": category,
        "criticality": criticality
    }
    
    # Process subcontrols if any
    if 'controls' in control:
        for subcontrol in control['controls']:
            process_control(subcontrol, controls, control_id)

def merge_with_existing(new_controls, existing_file):
    """Merge new controls with existing controls file"""
    try:
        with open(existing_file, 'r') as f:
            existing_controls = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load existing controls file: {e}")
        existing_controls = {}
    
    # Merge controls, new ones take precedence
    merged = {**existing_controls, **new_controls}
    logger.info(f"Merged controls: {len(existing_controls)} existing + {len(new_controls)} new = {len(merged)} total")
    
    return merged

def save_controls(controls, output_file):
    """Save controls to output file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(controls, f, indent=2)
        logger.info(f"Controls saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving controls: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_oscal_file> <output_controls_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Extract controls from OSCAL file
    controls = extract_controls(input_file)
    
    # If output file exists, merge with existing controls
    if os.path.exists(output_file):
        controls = merge_with_existing(controls, output_file)
    
    # Save to output file
    if save_controls(controls, output_file):
        print(f"Successfully processed {len(controls)} controls")
    else:
        print("Failed to save controls")
        sys.exit(1)

if __name__ == "__main__":
    main()
