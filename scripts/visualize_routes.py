#!/usr/bin/env python3
"""
Batch route visualization script
Generates viz_{src_id}_to_{tar_id}.png for all routes in a routes file
"""

import argparse
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.viz import FloorPlanVisualizer

def main():
    parser = argparse.ArgumentParser(description='Generate route visualizations')
    parser.add_argument('routes_file', help='Path to routes JSON file (e.g., routes/1_to_all.json)')
    parser.add_argument('--output-dir', '-o', default='visualizations', 
                       help='Output directory for visualizations')
    parser.add_argument('--limit', '-l', type=int, 
                       help='Limit number of routes to generate (for testing)')
    parser.add_argument('--line-width', type=int, default=8,
                       help='Width of route lines')
    parser.add_argument('--crop-padding', type=int, default=200,
                       help='Padding around route for cropping')
    parser.add_argument('--no-grid', action='store_true',
                       help='Don\'t show grid cells')
    parser.add_argument('--route-color', default='255,0,255',
                       help='Route line color as R,G,B (e.g., 255,0,255)')
    
    args = parser.parse_args()
    
    # Parse route color
    try:
        route_color = tuple(map(int, args.route_color.split(',')))
        if len(route_color) != 3:
            raise ValueError()
    except ValueError:
        print("Error: Invalid route color format. Use R,G,B (e.g., 255,0,255)")
        return 1
    
    # Initialize visualizer
    try:
        viz = FloorPlanVisualizer()
    except Exception as e:
        print(f"Error initializing visualizer: {e}")
        return 1
    
    # Set parameters
    viz.default_line_width = args.line_width
    viz.default_route_color = route_color
    viz.default_show_grid = not args.no_grid
    viz.default_crop_padding = args.crop_padding
    
    # Generate visualizations
    try:
        print(f"Loading routes from: {args.routes_file}")
        viz.visualize_routes_from_file(
            routes_file=args.routes_file,
            output_dir=args.output_dir,
            limit=args.limit
        )
        print(f"\nVisualization complete! Check {args.output_dir}/ for results.")
        
    except Exception as e:
        print(f"Error generating visualizations: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 