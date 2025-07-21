#!/usr/bin/env python3
"""
Script to parse booth data from SIGGRAPH HTML table.
Extracts name, URL, and booth_id for each exhibitor.
"""

import json
import re
from bs4 import BeautifulSoup

def parse_booth_data(html_file, output_file):
    """Parse booth data from HTML file and save to JSON."""
    
    # Read HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all table rows with booth data
    booth_rows = soup.find_all('tr', class_='js-List justify-between')
    
    booths = []
    url_prefix = "https://siggraph25.mapyourshow.com"
    
    for row in booth_rows:
        booth_data = {}
        
        # Extract name and url from the card title
        title_element = row.find('h3', class_='card-Title break-word dib f5 ma0')
        if title_element:
            link_element = title_element.find('a')
            if link_element:
                # Extract name
                name_span = link_element.find('span')
                if name_span:
                    booth_data['name'] = name_span.get_text(strip=True)
                
                # Extract URL
                href = link_element.get('href')
                if href:
                    booth_data['url'] = url_prefix + href
        
        # Extract booth_id from the floorplan link
        booth_subtitle = row.find('td', class_='card-Subtitle')
        if booth_subtitle:
            floorplan_link = booth_subtitle.find('a')
            if floorplan_link and 'floorplan_link.cfm' in floorplan_link.get('href', ''):
                booth_id = floorplan_link.get_text(strip=True)
                # Remove any HTML artifacts
                booth_id = re.sub(r'<!.*?>', '', booth_id).strip()
                booth_data['booth_id'] = booth_id
        
        # Only add booth if we have all required data
        if all(key in booth_data for key in ['name', 'url', 'booth_id']):
            booths.append(booth_data)
    
    # Save to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(booths, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(booths)} booth records")
    print(f"Data saved to: {output_file}")
    
    # Print first few records as sample
    if booths:
        print("\nSample records:")
        for i, booth in enumerate(booths[:3]):
            print(f"{i+1}. Name: {booth['name']}")
            print(f"   URL: {booth['url']}")
            print(f"   Booth ID: {booth['booth_id']}")
            print()

if __name__ == "__main__":
    input_file = "booth.html"
    output_file = "booth_data.json"
    
    try:
        parse_booth_data(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}")