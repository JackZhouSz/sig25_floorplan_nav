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
-   [ ] **Path Calculation**: Develop pathfinding algorithms (e.g., A*) to calculate routes between booths.
-   [ ] **Path Visualization**: Visualize the calculated paths on the map.
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

> For more detailed instructions on the OCR module, please refer to: [`docs/OCR_USAGE.md`](./docs/OCR_USAGE.md)

---

## �� Environment Setup

1.  **Clone the Project**:
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Install Python Dependencies**:
    It is recommended to use a virtual environment (e.g., `venv` or `conda`).
    ```bash
    # Create virtual environment
    python -m venv venv
    # Activate virtual environment
    source venv/bin/activate  # on Windows: venv\Scripts\activate
    
    # Install core dependencies
    pip install opencv-python numpy Pillow
    ```

3.  **Install and Configure Ollama (Required for OCR functionality)**:
    ```bash
    # 1. Install Ollama (if not already installed)
    curl -fsSL https://ollama.com/install.sh | sh

    # 2. Start Ollama service (usually starts automatically)
    ollama serve

    # 3. Download the vision model required for OCR
    ollama pull qwen2.5vl:7b
    
    # 4. Install Ollama Python client
    pip install ollama
    ```

## 📚 Detailed Documentation

-   [**Technical Tasks and Planning** (`task.md`)](./task.md): Deep dive into the design details, data flow, and historical progress of each module.
-   [**OCR Module Usage Guide** (`docs/OCR_USAGE.md`)](./docs/OCR_USAGE.md): Contains detailed parameter settings, troubleshooting, and advanced usage for the OCR module.
