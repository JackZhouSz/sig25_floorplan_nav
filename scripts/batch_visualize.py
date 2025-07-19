#!/usr/bin/env python3
"""
Advanced batch route visualization script
Generates viz_{src_id}_to_{tar_id}.png with type-based color coding
"""

import argparse
import json
import os
import sys
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.viz import FloorPlanVisualizer

# Route color schemes based on target types
TYPE_COLOR_SCHEMES = {
    'booth': {
        'route_color': (255, 50, 50),      # Red for booth-to-booth
        'line_width': 8,
        'description': 'Booth navigation'
    },
    'road': {
        'route_color': (50, 255, 50),      # Green for road access
        'line_width': 6,
        'description': 'Road/pathway access'
    },
    'exp hall': {
        'route_color': (255, 255, 50),     # Yellow for exhibition hall
        'line_width': 10,
        'description': 'Exhibition hall access'
    },
    'stage': {
        'route_color': (255, 150, 0),      # Orange for stage
        'line_width': 12,
        'description': 'Stage access'
    },
    'Lounge': {
        'route_color': (150, 150, 255),    # Light blue for lounge
        'line_width': 8,
        'description': 'Lounge access'
    },
    'default': {
        'route_color': (255, 0, 255),      # Magenta for others
        'line_width': 8,
        'description': 'General navigation'
    }
}

def get_route_style(target_type: str) -> Dict:
    """Get route styling based on target type"""
    return TYPE_COLOR_SCHEMES.get(target_type, TYPE_COLOR_SCHEMES['default'])

def main():
    parser = argparse.ArgumentParser(description='Generate type-based route visualizations')
    parser.add_argument('routes_file', help='Path to routes JSON file (e.g., routes/1_to_all.json)')
    parser.add_argument('--output-dir', '-o', default='visualizations_by_type', 
                       help='Output directory for visualizations')
    parser.add_argument('--limit', '-l', type=int, 
                       help='Limit number of routes to generate (for testing)')
    parser.add_argument('--crop-padding', type=int, default=150,
                       help='Padding around route for cropping')
    parser.add_argument('--no-grid', action='store_true',
                       help='Don\'t show grid cells')
    parser.add_argument('--uniform-color', 
                       help='Use uniform color for all routes (R,G,B)')
    parser.add_argument('--show-stats', action='store_true',
                       help='Show statistics of route types')
    
    args = parser.parse_args()
    
    # Load route data to analyze types
    with open(args.routes_file, 'r', encoding='utf-8') as f:
        routes_data = json.load(f)
    
    start_idx = routes_data['start_idx']
    start_cell = routes_data['start_cell']
    targets = routes_data['targets']
    
    # Analyze target types
    type_counts = {}
    for target_idx, route_data in targets.items():
        target_type = route_data['target_info']['type']
        type_counts[target_type] = type_counts.get(target_type, 0) + 1
    
    if args.show_stats:
        print(f"Route type statistics from {start_cell['name']} (idx: {start_idx}):")
        print("-" * 50)
        for type_name, count in sorted(type_counts.items()):
            style = get_route_style(type_name)
            print(f"{type_name:12}: {count:3} routes - {style['description']}")
        print("-" * 50)
        print(f"Total: {sum(type_counts.values())} routes")
        print()
    
    # Parse uniform color if provided
    uniform_color = None
    if args.uniform_color:
        try:
            uniform_color = tuple(map(int, args.uniform_color.split(',')))
            if len(uniform_color) != 3:
                raise ValueError()
        except ValueError:
            print("Error: Invalid uniform color format. Use R,G,B (e.g., 255,0,255)")
            return 1
    
    # Initialize visualizer
    try:
        viz = FloorPlanVisualizer()
    except Exception as e:
        print(f"Error initializing visualizer: {e}")
        return 1
    
    # Set common parameters
    viz.default_show_grid = not args.no_grid
    viz.default_crop_padding = args.crop_padding
    
    # Generate visualizations
    try:
        print(f"Generating visualizations from: {start_cell['name']} (idx: {start_idx})")
        print(f"Output directory: {args.output_dir}")
        
        count = 0
        for target_idx, route_data in targets.items():
            if args.limit and count >= args.limit:
                break
            
            target_info = route_data['target_info']
            target_type = target_info['type']
            
            # Get style for this target type
            style = get_route_style(target_type)
            
            # Override with uniform color if specified
            if uniform_color:
                route_color = uniform_color
                line_width = 8  # Default line width
            else:
                route_color = style['route_color']
                line_width = style['line_width']
            
            # Create type-specific subdirectory
            type_dir = os.path.join(args.output_dir, target_type)
            os.makedirs(type_dir, exist_ok=True)
            
            # Generate filename
            filename = f"viz_{start_idx}_to_{target_idx}.png"
            output_path = os.path.join(type_dir, filename)
            
            # Set visualization parameters
            viz.default_line_width = line_width
            viz.default_route_color = route_color
            
            # Draw the route
            viz.draw_route_on_map(route_data, output_path)
            
            print(f"Generated: {target_type}/{filename} -> {target_info['name']}")
            count += 1
        
        print(f"\nGenerated {count} route visualizations organized by type in {args.output_dir}/")
        
        # Print summary by type
        print("\nGenerated files by type:")
        for type_name in type_counts.keys():
            type_dir = os.path.join(args.output_dir, type_name)
            if os.path.exists(type_dir):
                file_count = len([f for f in os.listdir(type_dir) if f.endswith('.png')])
                print(f"  {type_name}: {file_count} files in {type_dir}/")
        
    except Exception as e:
        print(f"Error generating visualizations: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 