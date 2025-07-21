# Booth Detail Extraction

This module extracts exhibitor booth information from SIGGRAPH 2025 exhibition data.

## Overview

The booth detail extraction process consists of two main steps:
1. **Parse booth data** from HTML table (basic info)
2. **Fetch detailed information** from individual booth URLs (descriptions & categories)

## Workflow

### Step 1: Data Collection
1. Visit `https://siggraph25.mapyourshow.com/8_0/explore/exhibitor-gallery.cfm`
2. Expand all exhibitors to show complete list
3. Save the complete HTML page as `booth.html`

### Step 2: Basic Data Parsing
```bash
python scripts/booth_detail/parse_booth_data.py
```

This extracts:
- **name**: Exhibitor company name
- **url**: Link to detailed exhibitor page (with full domain prefix)
- **booth_id**: Exhibition booth number

Output: `booth_data.json`

### Step 3: Detailed Information Fetching
```bash
python scripts/booth_detail/fetch_booth_details.py
```

This adds:
- **description**: Company description (from HTML meta tags)
- **categories**: Exhibition categories (comma-separated)

Output: `booth_data_detailed.json`

## Data Structure

### Initial Data (booth_data.json)
```json
[
  {
    "name": "3dverse",
    "url": "https://siggraph25.mapyourshow.com/8_0/exhibitor/exhibitor-details.cfm?exhid=504294",
    "booth_id": "716"
  }
]
```

### Complete Data (booth_data_detailed.json)
```json
[
  {
    "name": "Abstract Group",
    "url": "https://siggraph25.mapyourshow.com/8_0/exhibitor/exhibitor-details.cfm?exhid=1080",
    "booth_id": "307",
    "description": "Abstract is a group of companies focused on developing bleeding-edge 3D technology. Our tech enables a diverse range of clients to deliver their projects on time, with massive cost-saving and on top of all, having much more fun while they're doing it.",
    "categories": "3D Graphics, 3D Modeling, 3D Scanning, Automotive Applications, CAD/CAM/CAE/CIM, Game Engines, Online Network Services, Plug-ins for Software, Rendering & Modeling"
  }
]
```

## Scripts

### parse_booth_data.py
- **Input**: `booth.html` (downloaded exhibition page)
- **Output**: `booth_data.json` (basic booth information)
- **Function**: Parses HTML table structure to extract exhibitor names, URLs, and booth IDs

### fetch_booth_details.py
- **Input**: `booth_data.json`
- **Output**: `booth_data_detailed.json` (complete booth information)
- **Function**: Visits each booth URL to extract descriptions and categories
- **Features**:
  - Progress saving every 10 booths
  - Rate limiting (0.5s delay between requests)
  - Error handling for failed requests
  - Extracts descriptions from HTML meta tags
  - Extracts categories from exhibition category lists

## Data Extraction Details

### Description Sources
1. **Primary**: HTML `<meta name="description" content="...">` tag
2. **Fallback**: `<div id="section-description">` content

### Category Sources
- `<div class="section--list__columns-wrapper">` containing category links
- Categories are joined with commas

## Usage Notes

### Dependencies
```bash
pip install beautifulsoup4 requests
```

### Customization
- Modify `max_booths` parameter in `fetch_booth_details.py` for testing
- Adjust `time.sleep()` delay for different rate limiting
- Progress is automatically saved to avoid data loss

### Error Handling
- Network timeouts are handled gracefully
- Missing descriptions/categories result in empty strings
- Progress is saved incrementally to prevent data loss

## Optional Enhancement

For booths missing descriptions, additional research can be conducted:
1. Web search for company information
2. Manual curation of missing descriptions
3. Integration with company databases or APIs

This would be implemented as a separate script to supplement the automated extraction process.