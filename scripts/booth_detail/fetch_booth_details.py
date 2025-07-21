#!/usr/bin/env python3
"""
Script to fetch detailed information from booth URLs.
Adds description and categories to existing booth data.
"""

import json
import re
import requests
import time
from bs4 import BeautifulSoup

def fetch_booth_details(url):
    """Fetch description and categories from a booth detail URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract description from meta tag
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        
        # Fallback: try section-description div
        if not description:
            desc_section = soup.find('div', id='section-description')
            if desc_section:
                desc_content = desc_section.find('div', class_='line-clamp__10 animated line-clamp')
                if desc_content:
                    description = desc_content.get_text(strip=True)
        
        # Extract categories
        categories = []
        cat_wrapper = soup.find('div', class_='section--list__columns-wrapper')
        if cat_wrapper:
            cat_links = cat_wrapper.find_all('a')
            for link in cat_links:
                category_text = link.get_text(strip=True)
                if category_text:
                    categories.append(category_text)
        
        return {
            'description': description,
            'categories': ', '.join(categories) if categories else ""
        }
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return {
            'description': "",
            'categories': ""
        }

def update_booth_data(json_file, start_index=0, max_booths=None):
    """Update booth data with description and categories."""
    
    # Load existing data
    with open(json_file, 'r', encoding='utf-8') as f:
        booths = json.load(f)
    
    # Limit processing for testing
    if max_booths:
        booths = booths[start_index:start_index + max_booths]
    
    print(f"Updating {len(booths)} booth records (starting from index {start_index})...")
    
    for i, booth in enumerate(booths):
        print(f"Processing {i+1}/{len(booths)}: {booth['name']}")
        
        # Fetch additional details
        details = fetch_booth_details(booth['url'])
        
        # Update booth data
        booth['description'] = details['description']
        booth['categories'] = details['categories']
        
        # Save progress directly to output file every 10 booths
        if (i + 1) % 10 == 0:
            output_file = json_file.replace('.json', '_detailed.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(booths, f, indent=2, ensure_ascii=False)
            print(f"Progress saved: {i + 1}/{len(booths)} booths processed")
        
        # Debug output for first few booths
        if i < 3:
            print(f"   Found description: {'Yes' if details['description'] else 'No'}")
            print(f"   Found categories: {'Yes' if details['categories'] else 'No'}")
        
        # Be nice to the server
        time.sleep(0.5)
    
    # Save updated data
    output_file = json_file.replace('.json', '_detailed.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(booths, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated data saved to: {output_file}")
    
    # Print sample of updated records
    if booths:
        print("\nSample updated records:")
        for i, booth in enumerate(booths[:2]):
            print(f"{i+1}. Name: {booth['name']}")
            print(f"   Booth ID: {booth['booth_id']}")
            print(f"   Description: {booth['description'][:100]}{'...' if len(booth['description']) > 100 else ''}")
            print(f"   Categories: {booth['categories']}")
            print()

if __name__ == "__main__":
    json_file = "booth_data.json"
    
    try:
        # Process all booths
        update_booth_data(json_file, start_index=0, max_booths=None)
    except Exception as e:
        print(f"Error: {e}")