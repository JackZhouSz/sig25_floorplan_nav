# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a venue/exhibition floorplan navigation system that converts web-based canvas maps into structured digital navigation with text-based directions. The system processes booth detection data, generates pathfinding routes, and provides natural language navigation instructions in Chinese.

## Common Commands

### Main Workflow Scripts
```bash
# Manual grid annotation (GUI tool)
python core/annotate.py

# Build type metadata from grid data
python scripts/build_type_metadata.py

# Batch OCR processing
python scripts/ocr_batch.py

# Apply OCR results to grid
python scripts/apply_ocr_results.py --backup

# Precompute routes from a start point to all booths
python scripts/precompute_routes.py --start 52 --allow-diag

# Visualize precomputed routes
python scripts/batch_visualize.py routes/52_to_all.json --show-stats

# Generate natural language navigation
python scripts/generate_navigation.py --start 52 --end 10

# Batch generate navigation for all targets
python scripts/generate_navigation.py --start 52 --batch

# Generate with custom configuration
python scripts/generate_navigation.py --start 52 --end 10 --config config/high_precision.yaml
```

### Automated Batch Processing
```batch
# Windows batch script for end-to-end route processing
run_routes.bat 52                    # Basic usage with start point 52
run_routes.bat 52 my_output true     # With custom output dir and diagonal movement
run_routes.bat 1 default false 0.5   # With turn weight penalty
```

### Testing
```bash
# Test OCR functionality
python scripts/test_ocr.py

# Test navigation text generation
python scripts/test_navigation.py
```

## Core Architecture

### Data Flow Pipeline
```
bboxes_*.json → data/grid.json → routes/*.json → navigation_results/*.txt
```

### Core Modules (`core/`)

- **`grid.py`**: Grid data structures and I/O. Defines `Cell` dataclass with booth metadata, coordinates, and type classification
- **`pathfinder.py`**: A* pathfinding with multi-source/target support, configurable movement (4/8-direction), turn costs via `PathfindingOptions`
- **`navigation.py`**: Natural language generation with `RouteAnalyzer` for turn detection and `RuleFormatter` for Chinese text output
- **`viz.py`**: Route visualization and map rendering
- **`ocr_ollama.py`**: OCR integration using Ollama vision models for booth name/ID extraction
- **`annotate.py`**: GUI tool for manual grid refinement

### Key Data Structures

- **Cell**: Core grid unit with `idx`, pixel coordinates `(x,y,w,h)`, unit coordinates `(col,row)`, `type`, `name`, `booth_id`
- **RouteResult**: Contains both semantic path (Cell idx sequence) and geometric path (unit coordinates)
- **PathfindingOptions**: Configures movement constraints (`allow_diag`, `turn_weight`, `allow_enter_area`)
- **NavigationStep**: Structured navigation instructions with landmarks and actions

### Processing Scripts (`scripts/`)

#### Grid Management
- `build_type_metadata.py`: Scans grid.json to create/update `data/grid_types.json` with type properties
- `check_grid_types.py`: Statistics and validation of grid type distribution

#### OCR Pipeline
- `ocr_batch.py`: Batch processes booth cells for name/ID extraction
- `apply_ocr_results.py`: Merges OCR results back into grid.json

#### Pathfinding & Visualization
- `precompute_routes.py`: Bulk A* computation from one source to all booths
- `batch_visualize.py`: Generates route visualization images grouped by type
- `visualize_routes.py`: Single route visualization tool

#### Navigation Text Generation
- `generate_navigation.py`: CLI for converting routes to Chinese navigation instructions
- `test_navigation.py`: Unit tests for navigation logic

### Configuration Files

- **`data/grid.json`**: Master grid data (authoritative source)
- **`data/grid_types.json`**: Type metadata defining walkability, costs, colors
- **`data/grid_meta.json`**: Unit size and coordinate system metadata
- **`data/ocr_results.json`**: OCR output before merging to grid
- **`config/*.yaml`**: Navigation system configuration files for different scenarios

## Current Development Phase

The project has completed **Phase 1.3 - Sequence Booth Counting System** of navigation text generation. Recent achievements:

### ✅ Completed Features
- **Coverage-based Landmark Selection**: Ensures landmarks described as "passing by" have sufficient visibility along the path
- **Sequence Booth Counting**: Booth count directly corresponds to landmark descriptions for semantic consistency
- **Intelligent Distance Grading**: Smart selection between booth counting, single landmarks, and multiple landmarks
- **YAML Configuration System**: Flexible parameter adjustment for different scenarios

### 🔧 Recent Improvements (Phase 1.3)
- **Problem Solved**: Fixed semantic inconsistency where system would say "5 booths" but only mention 1-2 landmarks
- **Technical Change**: Replaced four-direction path scanning with sequence-based counting
- **Result**: Perfect alignment between booth count and landmark descriptions

### 📊 System Status
- **Path Planning Success Rate**: 100% (92/92 paths)
- **Navigation Text Quality**: Human-verified Chinese natural language
- **OCR Recognition Accuracy**: >90%

### 🎯 Next Phase
- **Phase 2.0 - Orientation Calculation Optimization**: Improve side calculation logic for better left/right/front classification

## Documentation Structure

- **`arch.md`**: Complete system architecture documentation with design philosophy and technical decisions
- **`readme.md`**: English project overview and usage instructions
- **`readme_zh-tw.md`**: Chinese project overview and usage instructions  
- **`task.md`**: Detailed technical progress and historical development phases
- **`CLAUDE.md`**: This file - development guidance and current system status

## Cursor Rules Integration

- Read project documentation (`readme.md`, `task.md`, `arch.md`) to understand context
- For non-trivial tasks, organize `temp.md` with implementation details
- Confirm implementation items with user before proceeding unless explicitly told to proceed directly
- Use English for comments and documentation by default

## Dependencies

- **Python**: OpenCV, NumPy, Pillow for image processing
- **Ollama**: Vision model integration (`qwen2.5vl:7b`) for OCR
- **PyYAML**: YAML configuration file support
- **No package.json/requirements.txt**: Dependencies installed manually per README

## Key Technical Concepts

### Navigation System Architecture
- **Coverage Ratio**: `visible_length / total_path_length` - determines if a landmark should be described as "passing by"
- **Sequence Processing**: `coverage_sort → top_k_select → path_order_sort` for optimal landmark selection
- **Booth Counting Strategy**: Direct sequence counting ensures semantic consistency between descriptions and counts

### Configuration-Driven Development
- Use YAML configs in `config/` directory for different scenarios
- Test configuration changes without code modification
- Standard configs: `navigation_config.yaml`, `high_precision.yaml`, `simple_mode.yaml`

## Notebook Workflow

- `notebooks/single_detect.ipynb`: Process individual hover videos to extract bounding boxes
- `notebooks/01_build_grid.ipynb`: Merge multiple bbox files and compute grid units