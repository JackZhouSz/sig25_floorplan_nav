 # Exhibition Floor Plan Navigation Project

This project aims to create a digital solution for exhibition floor plans, with the ultimate goal of providing text-based navigation from a specific starting point (e.g., Dell booth) to other booths or areas.

## Project Goals and Prerequisites

-   **Goal**: To build a digitized exhibition floor plan that provides text-based navigation between booths.
-   **Prerequisites**:
    -   The original floor plan (https://siggraph25.mapyourshow.com/8_0/exhview/index.cfm) is in web Canvas Render format, making direct extraction of booth information difficult.
    -   The map Canvas highlights booths on hover, a characteristic we leverage for detection.
    -   Booth layouts on the map are grid-aligned.
    -   Leverage Computer Vision (CV) and Optical Character Recognition (OCR) technologies to parse the map.

## ✨ Task Progress (TODOs)

-   [x] **Grid Creation & Management**: Convert the map into structured grid data (`data/grid.json`).
-   [x] **Manual Annotation Tool**: Provide a GUI tool (`core/annotate.py`) for manual addition, modification, and deletion of grid cells.
-   [x] **OCR Information Extraction**: Automatically identify booth names and IDs and populate them into the grid data.
-   [x] **Path Calculation**: Implement A* algorithm (`core/pathfinder.py`) & batch pre-compute script (`scripts/precompute_routes.py`).
-   [x] **Path Visualization**: New visualization module (`core/viz.py`) & helper scripts (`scripts/visualize_routes.py`, `scripts/batch_visualize.py`).
-   [ ] **Text Navigation Generation**: Convert paths into natural language navigation instructions.

> For detailed technical planning and historical progress, please refer to: [`task.md`](./task.md)

---

## 📸 Pre-processing Steps (Data Preparation)

Before starting grid creation, we need to obtain the raw booth data from the online map.

1.  **Record Online Map**: Record a video of the online map, hovering over all booths one by one to highlight them.
    > **Note**: The map might be too large, requiring multiple recordings to cover all areas.

2.  **Process Individual Videos**: Use `notebooks/single_detect.ipynb` to process each recorded video, converting all highlighted booth areas into grid boxes on the large map, and saving the results as `bboxed_{i}.json`.
    ```
    notebooks/single_detect.ipynb
    ```

3.  **Merge and Calculate Grid Units**: Use `notebooks/01_build_grid.ipynb` to merge grid box data from multiple videos and calculate uniform grid units. This will generate `data/grid.json` as the primary grid data source.
    ```
    notebooks/01_build_grid.ipynb
    ```

---

## 🚀 Main Workflow

This project's workflow is designed with several independent but interconnected steps, allowing you to progressively transform a map image into complete navigation information.

### Step 1: Create and Refine the Grid
After completing the pre-processing steps to generate initial grid data, use manual tools for fine-tuning and supplementation.

1.  **Manual Annotation and Correction**: Use the GUI tool for fine-tuning. This is the most crucial step for ensuring data quality.
    ```bash
    python core/annotate.py
    ```
    -   **Operation**: Drag with the left mouse button to add new cells, right-click to modify or delete.
    -   **Goal**: Ensure all booths, walkways, and public areas are correctly labeled.

2.  **Build Type Metadata**: Scan the existing `type` fields in `grid.json` to automatically create or update `data/grid_types.json`.
    ```bash
    python scripts/build_type_metadata.py
    ```
    > **Important**: `data/grid_types.json` defines the properties of each cell type (e.g., whether it's walkable, display color, etc.), which is fundamental for path calculation. Make sure to run this step before starting OCR or path calculation.

### Step 2: Perform OCR Recognition
After grid creation, perform OCR to automatically fill in booth names and IDs.

1.  **Run Batch OCR**: This script will process all cells requiring identification.
    ```bash
    python scripts/ocr_batch.py
    ```
    > **Tip**: This process might take some time for the first run or with many cells. The script supports the `--limit` parameter for testing.

2.  **Manual Review and Correction**:
    -   Open the `data/ocr_results.json` file.
    -   Manually inspect and correct `name` or `booth_id` errors identified by the model.

3.  **Apply Corrections**: Write the corrected results back to the main `grid.json` file.
    ```bash
    python scripts/apply_ocr_results.py --backup
    ```

### Step 3: Path Calculation & Pre-compute

```python
# Compute a single route (interactive usage)
from core.pathfinder import Pathfinder
pf = Pathfinder()
route = pf.find_route(start_idx=1, target_idx=53)
print(route)
```
```bash
# Batch pre-compute from one booth to all others   
python scripts/precompute_routes.py --start 1
```

### Step 4: Path Visualization (NEW)

1.  **Quick preview (generate one or few routes)**
    ```bash
    python scripts/visualize_routes.py routes/1_to_all.json --limit 3
    ```
2.  **Generate all routes grouped by type (recommended)**
    ```bash
    python scripts/batch_visualize.py routes/1_to_all.json --show-stats
    ```
    -   Outputs to `visualizations_by_type/{type}/viz_{src}_to_{dst}.png`
    -   All cells are drawn with 30 % opacity; start/end cells highlighted.

>  For detailed parameters (`--crop-padding`, `--route-color`, etc.), run `-h` on each script.

---

## 📚 Detailed Documentation

-   [**Technical Tasks and Planning** (`task.md`)](./task.md): Deep dive into the design details, data flow, and historical progress of each module.
-   [**OCR Module Usage Guide** (`docs/OCR_USAGE.md`)](./docs/OCR_USAGE.md): Contains detailed parameter settings, troubleshooting, and advanced usage for the OCR module.
