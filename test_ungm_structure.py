"""Test UNGM HTML structure"""
from bs4 import BeautifulSoup

with open('ungm_debug.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# Check for div-based tables
div_tables = soup.find_all('div', role='table')
print(f"Div tables with role='table': {len(div_tables)}")

# Check for HTML tables
html_tables = soup.find_all('table')
print(f"HTML <table> elements: {len(html_tables)}")

if div_tables:
    tbl = div_tables[0]
    print(f"\nDiv table ID: {tbl.get('id', 'N/A')}")
    
    # Find all rows
    all_rows = tbl.find_all('div', role='row')
    print(f"All div rows: {len(all_rows)}")
    
    # Find header rowgroup
    header_group = tbl.find('div', role='rowgroup', class_='tableHead')
    if header_group:
        header_rows = header_group.find_all('div', role='row')
        print(f"Header rows: {len(header_rows)}")
        if header_rows:
            header_cells = header_rows[0].find_all('div', role='columnheader')
            print(f"Header cells: {len(header_cells)}")
            print(f"Header text: {[c.get_text().strip()[:20] for c in header_cells]}")
    
    # Find body rowgroup
    body_group = tbl.find('div', role='rowgroup', class_='tableBody')
    if body_group:
        body_rows = body_group.find_all('div', role='row')
        print(f"Body rows: {len(body_rows)}")
        if body_rows:
            # Check first data row
            first_row = body_rows[0]
            cells = first_row.find_all('div', role='cell')
            print(f"First row cells: {len(cells)}")
            # Find title cell (should have class="resultTitle")
            title_cell = first_row.find('div', class_='resultTitle')
            if title_cell:
                title_link = title_cell.find('a')
                if title_link:
                    print(f"Title: {title_link.get_text().strip()[:80]}")
                    print(f"Title link: {title_link.get('href', 'N/A')}")
                else:
                    title_span = title_cell.find('span', class_='ungm-title')
                    if title_span:
                        print(f"Title (from span): {title_span.get_text().strip()[:80]}")
else:
    print("\nNo div-based tables found!")
    if html_tables:
        print(f"Found {len(html_tables)} HTML tables instead")
