import asyncio
import hashlib
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

import httpx
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, VirtualScrollConfig
from services.content_filter import filter_relevant_content

# Fix Windows encoding (event loop policy is set in main.py before uvicorn starts)
if sys.platform == 'win32':
    # Set UTF-8 encoding for Windows console
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass


def generate_item_id(url: str, title: str, pub_date: str) -> str:
    """Generates a unique ID for a scraped item"""
    if url:
        return hashlib.md5(url.encode()).hexdigest()[:50]
    # Fallback to title + date
    combined = f"{title}_{pub_date}"
    return hashlib.md5(combined.encode()).hexdigest()[:50]


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Get text and clean it up
    text = soup.get_text()
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text


def extract_images_from_html(html: str) -> List[str]:
    """Extract image URLs from HTML"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    images = []
    
    # Find all img tags
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if src:
            # Convert relative URLs to absolute if needed
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                # Would need base URL to make absolute
                pass
            images.append(src)
    
    return images[:5]  # Return first 5 images


def extract_meta_info(html: str) -> Dict[str, str]:
    """Extract meta tags (description, og:image, etc.) from HTML"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    meta_info = {}
    
    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
    if meta_desc:
        meta_info['description'] = meta_desc.get('content', '')
    
    # Extract og:image
    og_image = soup.find('meta', attrs={'property': 'og:image'})
    if og_image:
        meta_info['image'] = og_image.get('content', '')
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        meta_info['title'] = title_tag.get_text().strip()
    
    return meta_info


def parse_paktender_date(date_str: str) -> str:
    """
    Parse paktender.com date format to ISO format (YYYY-MM-DD)
    Handles multiple formats:
    - DD-MM-YYYY (e.g., "22-01-2026")
    - Date strings with labels like "Publish:08-01-2026 Deadline:28-01-2026"
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO format date string (YYYY-MM-DD) or current date if parsing fails
    """
    try:
        # Clean the date string - remove bold markers and extra whitespace
        date_str = date_str.replace('**', '').strip()
        
        # Try to extract date from format like "Publish:08-01-2026 Deadline:28-01-2026"
        if 'Deadline:' in date_str:
            # Extract deadline date
            deadline_part = date_str.split('Deadline:')[1].strip()
            # Remove time if present (e.g., "28-01-2026 Time:10:00 AM")
            if 'Time:' in deadline_part:
                deadline_part = deadline_part.split('Time:')[0].strip()
            date_str = deadline_part
        elif 'Publish:' in date_str:
            # Extract publish date if no deadline
            publish_part = date_str.split('Publish:')[1].strip()
            if 'Deadline:' in publish_part:
                publish_part = publish_part.split('Deadline:')[0].strip()
            date_str = publish_part
        
        # Parse DD-MM-YYYY format
        parts = date_str.strip().split('-')
        if len(parts) == 3:
            day, month, year = parts
            # Convert to ISO format YYYY-MM-DD
            iso_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return iso_date
    except Exception:
        pass
    
    # Return current date if parsing fails
    return datetime.now().strftime("%Y-%m-%d")


def extract_paktender_table(html: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract tender opportunities from paktender.com table
    
    Args:
        html: HTML content from paktender.com
        url_config: Configuration for this source
        
    Returns:
        List of opportunity items extracted from the table
    """
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Find the table containing tenders
    # Look for table with "Latest Tenders" or similar structure
    tables = soup.find_all('table')
    print(f"  Found {len(tables)} table(s) on page")
    
    if len(tables) == 0:
        print(f"  ⚠ No tables found - page structure may have changed")
        # Try to find table by looking for "Latest Tenders" heading
        h2_tags = soup.find_all(['h1', 'h2', 'h3'])
        for h2 in h2_tags:
            if 'tender' in h2.get_text().lower():
                print(f"  Found heading: {h2.get_text()}")
    
    for table_idx, table in enumerate(tables):
        print(f"  Processing table {table_idx + 1}...")
        # Find all rows in the table (skip header row)
        rows = table.find_all('tr')
        print(f"    Found {len(rows)} rows in table {table_idx + 1}")
        
        if len(rows) == 0:
            print(f"    ⚠ Table {table_idx + 1} has no rows")
            continue
        
        # Skip first row if it's a header
        if len(rows) > 0:
            # Check if first row looks like a header (contains "TSC No", "Detail", etc.)
            first_row_text = rows[0].get_text().lower()
            if 'tsc no' in first_row_text or 'detail' in first_row_text or 'procurement' in first_row_text:
                rows = rows[1:]  # Skip header row
                print(f"    Skipped header row, processing {len(rows)} data rows")
        
        # Process each row
        rows_processed = 0
        for row in rows:
            cells = row.find_all(['td', 'th'])
            
            # New table structure: TSC No, Detail, Procurement Agency, Type, Regulator, Date, Days Remaining, Status, Attachments
            # We need at least 9 columns to get all fields
            if len(cells) >= 6:
                try:
                    tsc_no = cells[0].get_text().strip()
                    detail = cells[1].get_text().strip()
                    procurement_agency = cells[2].get_text().strip() if len(cells) > 2 else ""
                    tender_type = cells[3].get_text().strip() if len(cells) > 3 else ""
                    regulator = cells[4].get_text().strip() if len(cells) > 4 else ""
                    date_info = cells[5].get_text().strip() if len(cells) > 5 else ""  # Contains both publish and deadline dates
                    days_remaining = cells[6].get_text().strip() if len(cells) > 6 else ""
                    status = cells[7].get_text().strip() if len(cells) > 7 else ""
                    attachments_cell = cells[8] if len(cells) > 8 else None
                    
                    # Skip if essential fields are empty
                    if not detail or not tsc_no:
                        continue
                    
                    # Extract link from the detail cell (this is the link to the specific tender page)
                    item_link = url_config['url']  # Default to base URL
                    detail_cell = cells[1]  # Detail is in the second cell
                    link_tag = detail_cell.find('a', href=True)
                    if link_tag:
                        href = link_tag.get('href', '')
                        if href:
                            # Convert relative URLs to absolute
                            from urllib.parse import urljoin
                            base_url = 'https://paktender.com'  # Base URL for constructing absolute links
                            if href.startswith('http'):
                                item_link = href
                            elif href.startswith('/'):
                                item_link = urljoin(base_url, href)
                            else:
                                # Relative path like "tender-share.php?id=3871"
                                item_link = urljoin(base_url, href)
                    
                    # Extract PDF attachments from the Attachments column
                    attachments = []
                    if attachments_cell:
                        # Find all links in the attachments cell
                        attachment_links = attachments_cell.find_all('a', href=True)
                        for att_link in attachment_links:
                            href = att_link.get('href', '')
                            title = att_link.get('title', '') or att_link.get_text().strip() or att_link.get('aria-label', '')
                            
                            # Check if it's a document link (PDF, Document, Report, NIT, BOQ, Bidding)
                            is_document = (
                                href and (
                                    href.endswith('.pdf') or 
                                    'pdf' in href.lower() or 
                                    'Document' in title or 
                                    'Report' in title or
                                    'NIT' in title or
                                    'BOQ' in title or
                                    'Bidding' in title or
                                    'html?id=' in href  # BPPRA document links
                                )
                            )
                            
                            if is_document:
                                # Convert to absolute URL
                                from urllib.parse import urljoin
                                if href.startswith('http'):
                                    doc_name = title if title else (href.split('/')[-1] or "Document")
                                    attachments.append({
                                        "name": doc_name,
                                        "url": href
                                    })
                                else:
                                    abs_url = urljoin('https://paktender.com', href)
                                    doc_name = title if title else (href.split('/')[-1] or "Document")
                                    attachments.append({
                                        "name": doc_name,
                                        "url": abs_url
                                    })
                    
                    # Parse dates from the Date column (format: "Publish:08-01-2026 Deadline:28-01-2026 Time:10:00 AM")
                    # Extract advertised and closing dates
                    advertised_iso = datetime.now().strftime("%Y-%m-%d")  # Default to current date
                    closing_iso = datetime.now().strftime("%Y-%m-%d")  # Default to current date
                    
                    if 'Publish:' in date_info:
                        publish_part = date_info.split('Publish:')[1]
                        if 'Deadline:' in publish_part:
                            publish_date_str = publish_part.split('Deadline:')[0].strip()
                            advertised_iso = parse_paktender_date(publish_date_str)
                    
                    if 'Deadline:' in date_info:
                        deadline_part = date_info.split('Deadline:')[1]
                        if 'Time:' in deadline_part:
                            deadline_date_str = deadline_part.split('Time:')[0].strip()
                        else:
                            deadline_date_str = deadline_part.strip()
                        closing_iso = parse_paktender_date(deadline_date_str)
                    
                    # Create opportunity item
                    item = {
                        "id": generate_item_id(f"{url_config['url']}#{tsc_no}", detail, closing_iso),
                        "title": detail[:200] if len(detail) > 200 else detail,  # Use detail as title
                        "link": item_link,  # Link to specific tender page (from Detail column)
                        "description": detail[:500],  # Full detail as description
                        "content": detail,  # Full detail as content
                        "pubDate": advertised_iso,  # Use advertised date as publication date
                        "deadline": closing_iso,  # Store closing date as deadline
                        "author": procurement_agency or url_config.get('name', 'Unknown'),
                        "categories": ["tender", "pakistan"] + ([tender_type] if tender_type else []),  # Add tender, pakistan, and type
                        "source": {
                            "id": url_config["id"],
                            "name": url_config["name"],
                            "url": url_config["url"]
                        },
                        "image": None,
                        # Additional fields specific to paktender
                        "tsc_no": tsc_no,
                        "procurement_agency": procurement_agency,
                        "tender_type": tender_type,
                        "regulator": regulator,
                        "days_remaining": days_remaining,
                        "status": status,
                        "attachments": attachments,  # List of PDF attachments
                        "opportunity_type": "Tender",  # All items from paktender are tenders
                        "country": "Pakistan",
                        "location": "Pakistan",
                    }
                    
                    items.append(item)
                    rows_processed += 1
                    
                except Exception as e:
                    # Skip rows that can't be parsed
                    print(f"    ⚠ Skipping row due to parsing error: {str(e)}")
                    continue
        
        print(f"    Successfully processed {rows_processed} items from table {table_idx + 1}")
    
    print(f"  Total items extracted: {len(items)}")
    return items


def parse_ungm_date(date_str: str) -> str:
    """
    Parse UNGM date format to ISO format (YYYY-MM-DD)
    Handles various date formats from UNGM
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Clean the date string
        date_str = date_str.strip()
        
        # Try common formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
        # Format: DD/MM/YYYY or DD-MM-YYYY
        date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if date_match:
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = '20' + year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Format: YYYY-MM-DD
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str[:10]
        
        # Try parsing with datetime if available
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(date_str, fuzzy=True)
            return parsed.strftime("%Y-%m-%d")
        except:
            pass
    except:
        pass
    
    return datetime.now().strftime("%Y-%m-%d")


def extract_ungm_notices(html: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract procurement notices from UNGM.org table
    Table columns: Title, Deadline, Published, Organization, Type of opportunity, Reference, Beneficiary country or territory
    
    Args:
        html: HTML content from UNGM.org
        url_config: Configuration for this source
        
    Returns:
        List of opportunity items extracted from the table
    """
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # UNGM uses divs with ARIA roles, not actual HTML table elements!
    # Structure: <div role="table" id="tblNotices"> with <div role="row"> and <div role="cell">
    # Look for: <div role="table" id="tblNotices">
    div_tables = soup.find_all('div', role='table')
    print(f"  Found {len(div_tables)} div-based table(s) with role='table'")
    
    # Also check for regular HTML tables (in case structure changes)
    html_tables = soup.find_all('table')
    print(f"  Found {len(html_tables)} HTML <table> element(s)")
    
    # Use div-based tables if found, otherwise fall back to HTML tables
    if div_tables:
        print(f"  Using div-based table structure (UNGM's actual format)")
        tables = div_tables
    else:
        print(f"  Using HTML table structure (fallback)")
        tables = html_tables
    
    
    for table_idx, table in enumerate(tables):
        print(f"  Processing table {table_idx + 1}...")
        
        # Check if this is a div-based table or HTML table
        is_div_table = table.name == 'div' and table.get('role') == 'table'
        
        if is_div_table:
            # Div-based table: look for <div role="row">
            rows = table.find_all('div', role='row')
            print(f"    Found {len(rows)} div rows (role='row') in table {table_idx + 1}")
        else:
            # HTML table: look for <tr>
            rows = table.find_all('tr')
            print(f"    Found {len(rows)} HTML rows (<tr>) in table {table_idx + 1}")
        
        if len(rows) == 0:
            print(f"    ⚠ Skipping table {table_idx + 1} - no rows found")
            continue
        
        # Find header row to determine column indices
        # UNGM results table has headers: Title, Deadline, Published, Organization, Type of opportunity, Reference, Beneficiary country or territory
        header_row = None
        header_cells = []
        
        if is_div_table:
            # For div-based tables, header is in <div role="rowgroup" class="tableHead">
            # Find the header rowgroup first
            header_rowgroup = table.find('div', role='rowgroup', class_='tableHead')
            if header_rowgroup:
                header_row = header_rowgroup.find('div', role='row')
                if header_row:
                    header_cells = header_row.find_all('div', role='columnheader')
                    if not header_cells:
                        # Fallback: look for divs with class containing "header"
                        header_cells = header_row.find_all('div', class_=lambda x: x and 'header' in x.lower())
                    print(f"    ✓ Found div-based table header row with {len(header_cells)} columns")
        else:
            # HTML table: look for header row with <th> elements
            for row in rows:
                cells = row.find_all('th')
                if len(cells) >= 5:
                    cell_texts = [cell.get_text().strip().lower() for cell in cells]
                    cell_texts_joined = ' '.join(cell_texts)
                    has_title = 'title' in cell_texts_joined
                    has_other_columns = any(keyword in cell_texts_joined for keyword in ['deadline', 'published', 'organization', 'type', 'reference', 'beneficiary'])
                    
                    if has_title and has_other_columns:
                        header_row = row
                        header_cells = cells
                        print(f"    ✓ Found HTML table header row with {len(header_cells)} columns")
                        break
        
        # If no header found, this might not be the results table (could be the filter form table)
        if not header_row:
            print(f"    ⚠ Skipping table {table_idx + 1} - no results table header found (might be filter form)")
            continue
        
        # Determine column indices based on header
        col_indices = {
            'title': 0,
            'deadline': 1,
            'published': 2,
            'organization': 3,
            'type': 4,
            'reference': 5,
            'beneficiary': 6
        }
        
        if header_row:
            header_texts = [cell.get_text().strip().lower() for cell in header_cells]
            # Map header text to column indices
            for idx, header_text in enumerate(header_texts):
                if 'title' in header_text:
                    col_indices['title'] = idx
                elif 'deadline' in header_text:
                    col_indices['deadline'] = idx
                elif 'published' in header_text:
                    col_indices['published'] = idx
                elif 'organization' in header_text:
                    col_indices['organization'] = idx
                elif 'type' in header_text or 'opportunity' in header_text:
                    col_indices['type'] = idx
                elif 'reference' in header_text:
                    col_indices['reference'] = idx
                elif 'beneficiary' in header_text or 'country' in header_text or 'territory' in header_text:
                    col_indices['beneficiary'] = idx
        
        # Process data rows (skip header)
        rows_processed = 0
        
        if is_div_table:
            # For div-based tables, data rows are in <div role="rowgroup" class="tableBody">
            data_rowgroup = table.find('div', role='rowgroup', class_='tableBody')
            if data_rowgroup:
                data_rows = data_rowgroup.find_all('div', role='row')
                print(f"    Found {len(data_rows)} data rows in tableBody")
            else:
                # Fallback: use all rows except header
                data_rows = [r for r in rows if r != header_row]
                print(f"    Using all rows except header ({len(data_rows)} rows)")
        else:
            # HTML table: use all rows except header
            data_rows = [r for r in rows if r != header_row]
        
        for row in data_rows:
            # Get cells based on table type
            if is_div_table:
                # Div-based: look for <div role="cell"> (data rows)
                cells = row.find_all('div', role='cell')
                # If no cells with role="cell", try to find divs with class="tableCell"
                if not cells:
                    cells = row.find_all('div', class_=lambda x: x and 'tableCell' in x)
            else:
                # HTML table: look for <td> (data cells, not <th>)
                cells = row.find_all('td')
            
            # Need at least 5 columns to be a valid notice row
            if len(cells) < 5:
                continue
            
            try:
                # Extract fields based on column indices
                title_cell = cells[col_indices['title']] if col_indices['title'] < len(cells) else None
                deadline_cell = cells[col_indices['deadline']] if col_indices['deadline'] < len(cells) else None
                published_cell = cells[col_indices['published']] if col_indices['published'] < len(cells) else None
                organization_cell = cells[col_indices['organization']] if col_indices['organization'] < len(cells) else None
                type_cell = cells[col_indices['type']] if col_indices['type'] < len(cells) else None
                reference_cell = cells[col_indices['reference']] if col_indices['reference'] < len(cells) else None
                beneficiary_cell = cells[col_indices['beneficiary']] if col_indices['beneficiary'] < len(cells) else None
                
                # Extract title and link
                # UNGM structure: Title is in <span class="ungm-title"> inside the cell
                # Link is in <a> tag, but link text is "Open in a new window", not the title
                title = ""
                item_link = ""
                if title_cell:
                    # First, try to find the title span (this is the actual title)
                    # UNGM uses class="ungm-title" or "ungm-title ungm-title--small"
                    title_span = title_cell.find('span', class_=lambda x: x and 'ungm-title' in x)
                    if title_span:
                        title = title_span.get_text().strip()
                        print(f"    ✓ Extracted title from span: {title[:60]}...")
                    
                    # If no title span, try to find text in the cell that's not from buttons/links
                    if not title:
                        # Get all text, but exclude button text and link icons
                        all_text = title_cell.get_text(separator=' ', strip=True)
                        # Remove common UI elements
                        title = all_text.replace('Express Interest', '').replace('Open in a new window', '').strip()
                        # Split by newlines and take the longest line (likely the title)
                        lines = [line.strip() for line in title.split('\n') if line.strip() and len(line.strip()) > 5]
                        if lines:
                            title = max(lines, key=len)  # Get the longest line
                    
                    # Find the link to the notice
                    # Link is usually in an <a> tag with href="/Public/Notice/XXXXX"
                    title_link = title_cell.find('a', href=True)
                    if not title_link:
                        # Try finding link anywhere in the row
                        row_links = row.find_all('a', href=True)
                        for link in row_links:
                            href = link.get('href', '')
                            if '/Public/Notice/' in href or '/Notice/' in href:
                                title_link = link
                                break
                    
                    if title_link:
                        href = title_link.get('href', '')
                        from urllib.parse import urljoin
                        if href.startswith('http'):
                            item_link = href
                        elif href.startswith('/'):
                            item_link = urljoin('https://www.ungm.org', href)
                        else:
                            item_link = urljoin('https://www.ungm.org/Public/Notice', href)
                
                # Final validation - if title is still empty or just a number, skip
                if not title or (len(title) <= 3 and title.isdigit()):
                    print(f"    ⚠ Skipping row - could not extract valid title (got: '{title}')")
                    if title_cell:
                        print(f"      Title cell text: {title_cell.get_text(separator=' ', strip=True)[:100]}")
                    continue
                
                
                # If no link found, construct one from reference or use a default
                if not item_link:
                    # Try to construct link from reference if available
                    if reference_cell:
                        ref_text = reference_cell.get_text().strip()
                        # UNGM notice links often follow pattern: /Public/Notice/ShowNotice.aspx?id=XXXXX
                        if ref_text:
                            # Try to find a link with this reference
                            ref_links = row.find_all('a', href=True)
                            for link in ref_links:
                                href = link.get('href', '')
                                if ref_text in href or 'ShowNotice' in href:
                                    from urllib.parse import urljoin
                                    if href.startswith('http'):
                                        item_link = href
                                    elif href.startswith('/'):
                                        item_link = urljoin('https://www.ungm.org', href)
                                    break
                
                # Final fallback: use the base URL if no link found
                if not item_link:
                    item_link = url_config['url']
                
                # Extract deadline
                deadline_text = deadline_cell.get_text().strip() if deadline_cell else ""
                closing_iso = parse_ungm_date(deadline_text)
                
                # Extract published date
                published_text = published_cell.get_text().strip() if published_cell else ""
                advertised_iso = parse_ungm_date(published_text)
                
                # Extract organization
                organization = organization_cell.get_text().strip() if organization_cell else "UNGM"
                
                # Extract type of opportunity
                opp_type = type_cell.get_text().strip() if type_cell else "Tender"
                
                # Extract reference
                reference = reference_cell.get_text().strip() if reference_cell else ""
                
                # Extract beneficiary country
                beneficiary = beneficiary_cell.get_text().strip() if beneficiary_cell else ""
                
                # Build description from available fields
                description_parts = []
                if organization and organization != "UNGM":
                    description_parts.append(f"Organization: {organization}")
                if opp_type:
                    description_parts.append(f"Type: {opp_type}")
                if beneficiary:
                    description_parts.append(f"Beneficiary: {beneficiary}")
                if reference:
                    description_parts.append(f"Reference: {reference}")
                
                description = ". ".join(description_parts) if description_parts else title[:500]
                
                # Determine opportunity type from type field
                opportunity_type = "Tender"
                if opp_type:
                    opp_type_lower = opp_type.lower()
                    if 'rfp' in opp_type_lower or 'request for proposal' in opp_type_lower:
                        opportunity_type = "RFP"
                    elif 'grant' in opp_type_lower:
                        opportunity_type = "Grant"
                    elif 'partnership' in opp_type_lower:
                        opportunity_type = "Partnership"
                
                # Build categories
                categories = ["procurement", "tender", "united nations", "un"]
                if beneficiary:
                    categories.append(beneficiary.lower())
                if opp_type:
                    categories.append(opp_type.lower())
                
                item = {
                    "id": generate_item_id(item_link if item_link else title, title, closing_iso),
                    "title": title[:200] if len(title) > 200 else title,
                    "link": item_link if item_link else url_config['url'],
                    "description": description[:500] if len(description) > 500 else description,
                    "content": description,
                    "pubDate": advertised_iso,
                    "deadline": closing_iso,
                    "author": organization or url_config.get('name', 'UNGM'),
                    "categories": categories,
                    "source": {
                        "id": url_config["id"],
                        "name": url_config["name"],
                        "url": url_config["url"]
                    },
                    "image": None,
                    "opportunity_type": opportunity_type,
                }
                
                # Add additional fields
                if reference:
                    item["reference_number"] = reference
                if beneficiary:
                    item["beneficiary_country"] = beneficiary
                if organization:
                    item["organization"] = organization
                
                items.append(item)
                rows_processed += 1
                
                # Debug: Log first few items to verify extraction
                if rows_processed <= 3:
                    print(f"    ✓ Extracted item {rows_processed}: '{title[:60]}...' (Link: {item_link[:80] if item_link else 'N/A'})")
                
            except Exception as e:
                print(f"    ⚠ Skipping row due to parsing error: {str(e)}")
                import traceback
                print(f"      Traceback: {traceback.format_exc()}")
                continue
        
        print(f"    Successfully processed {rows_processed} notices from table {table_idx + 1}")
    
    print(f"  Total extracted {len(items)} notices")
    return items


async def scrape_paktender_pages(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch PakTender listing with plain HTTP (no browser).

    Why: the HTML table is server-rendered; Crawl4AI adds cost/fragility.
    Parses pages 1–2 and keeps tenders whose deadline is today or later when parseable.
    """
    url = url_config["url"]
    print(f"  Detected PakTender — httpx table scrape: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    all_items: List[Dict[str, Any]] = []
    today = datetime.now().strftime("%Y-%m-%d")

    async with httpx.AsyncClient(follow_redirects=True, timeout=45.0, headers=headers) as client:
        for page in (1, 2):
            page_url = url if page == 1 else (f"{url}&page={page}" if "?" in url else f"{url}?page={page}")
            try:
                response = await client.get(page_url)
                response.raise_for_status()
                page_items = extract_paktender_table(response.text, url_config)
                print(f"  Page {page}: extracted {len(page_items)} rows")
                all_items.extend(page_items)
            except Exception as e:
                print(f"  ⚠ Page {page} failed: {e}")

    # Dedupe by id / link
    seen = set()
    unique = []
    for item in all_items:
        key = item.get("id") or item.get("link")
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    # Prefer open deadlines when we have a parseable deadline
    open_items = []
    for item in unique:
        deadline = (item.get("deadline") or "")[:10]
        if deadline and len(deadline) == 10 and deadline < today:
            continue
        open_items.append(item)

    print(f"✓ {url_config['name']}: {len(open_items)} open tenders (from {len(unique)} unique rows)")
    return open_items


async def scrape_ungm_with_scroll(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape UNGM.org notices with browser scroll (JS-rendered role=table).

    skip_keyword_filter / skip_ai_filter: keep all open notices (portal is already procurement).
    Expired deadlines are dropped when parseable.
    """
    url = url_config["url"]
    keywords = url_config.get("keywords", [])
    skip_keyword = url_config.get("skip_keyword_filter") or url_config.get("skip_ai_filter")
    scraped_items: List[Dict[str, Any]] = []

    print("  Detected UNGM — browser scroll scrape...")
    print(f"  URL: {url}")

    browser_cfg = BrowserConfig(
        headless=True,
        viewport_width=1400,
        viewport_height=900,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )

    # UNGM renders notices in div[role=table]#tblNotices after JS loads
    virtual_scroll_config = VirtualScrollConfig(
        container_selector="body, #tblNotices, [role='table']",
        scroll_count=20,
        scroll_by="page_height",
        wait_after_scroll=2.0,
    )

    crawler_config = CrawlerRunConfig(
        word_count_threshold=10,
        remove_overlay_elements=True,
        screenshot=False,
        wait_for_images=False,
        cache_mode=CacheMode.BYPASS,
        virtual_scroll_config=virtual_scroll_config,
        scan_full_page=True,
        page_timeout=180000,
        wait_until="domcontentloaded",
        delay_before_return_html=4.0,
    )

    try:
        async with AsyncWebCrawler(config=browser_cfg, verbose=False) as crawler:
            print("  Loading UNGM page with virtual scroll...")
            result = await crawler.arun(url=url, config=crawler_config)

            if not result.success:
                print(f"✗ Error loading UNGM page: {result.error_message}")
                return []

            html_content = result.html or ""
            print(f"  HTML length after virtual scroll: {len(html_content)}")

            if "tblNotices" in html_content or 'role="table"' in html_content:
                print("  ✓ Found UNGM table markers in HTML")
            else:
                print("  ⚠ WARNING: UNGM table markers not found — page may not have rendered")

            all_notices = extract_ungm_notices(html_content, url_config)
            print(f"  Total notices extracted: {len(all_notices)}")

            today = datetime.now().strftime("%Y-%m-%d")

            for item in all_notices:
                deadline = (item.get("deadline") or "")[:10]
                if deadline and len(deadline) == 10 and deadline < today:
                    continue

                if skip_keyword:
                    scraped_items.append(item)
                    continue

                is_relevant = filter_relevant_content(item, keywords)

                if not is_relevant:
                    beneficiary = item.get("beneficiary_country", "").lower()
                    if beneficiary:
                        region_keywords = [
                            "pakistan", "mena", "middle east", "north africa",
                            "arab", "gulf", "saudi", "uae", "egypt", "jordan", "lebanon",
                        ]
                        if any(region in beneficiary for region in region_keywords):
                            is_relevant = True

                if not is_relevant:
                    has_org = item.get("organization", "")
                    has_type = item.get("opportunity_type", "")
                    has_beneficiary = item.get("beneficiary_country", "")
                    if has_org and has_type and has_beneficiary:
                        is_relevant = True

                if is_relevant:
                    scraped_items.append(item)

            print(
                f"✓ {url_config['name']}: {len(scraped_items)} notices kept "
                f"(from {len(all_notices)} extracted)"
            )
            return scraped_items

    except Exception as e:
        print(f"✗ UNGM scrape error: {e}")
        return []


def extract_secp_notifications(html: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract notifications from SECP (https://www.secp.gov.pk/laws/notifications)
    Table structure: Date | Title | Download
    We only keep these three fields.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    from datetime import datetime, timedelta

    base_url = "https://www.secp.gov.pk"
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []

    # Find the table that has headers: Date, Title, Download
    target_table = None
    tables = soup.find_all("table")

    for table in tables:
        header_row = None
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
        if not header_row:
            header_row = table.find("tr")
        if not header_row:
            continue

        header_cells = header_row.find_all(["th", "td"])
        header_texts = [c.get_text(strip=True).lower() for c in header_cells]

        if (
            any("date" in h for h in header_texts)
            and any("title" in h for h in header_texts)
            and any("download" in h for h in header_texts)
        ):
            target_table = table
            break

    if not target_table:
        print("⚠ Could not find SECP notifications table (no matching headers)")
        return []

    # Get all data rows (skip header)
    tbody = target_table.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
    else:
        all_rows = target_table.find_all("tr")
        rows = all_rows[1:] if len(all_rows) > 1 else []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        raw_date = cells[0].get_text(strip=True)
        title = cells[1].get_text(strip=True)

        # Download link
        download_url = None
        link_tag = cells[2].find("a", href=True)
        if link_tag:
            href = link_tag.get("href", "")
            if href:
                download_url = urljoin(base_url, href)

        if not title and not download_url:
            continue

        # Parse date into ISO if possible
        pub_iso = datetime.now().isoformat()
        if raw_date:
            parsed = None
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y"):
                try:
                    parsed = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            if parsed:
                pub_iso = parsed.isoformat()

        item = {
            "id": generate_item_id(download_url or url_config["url"], title or raw_date, pub_iso),
            "title": title or "SECP Notification",
            "link": download_url or url_config["url"],
            "description": title or "",
            "content": "",  # only date/title/download
            "pubDate": pub_iso,
            "author": url_config.get("name", "SECP"),
            "categories": ["notification", "secp", "pakistan"],
            "source": {
                "id": url_config["id"],
                "name": url_config["name"],
                "url": url_config["url"],
            },
            "image": None,
            "notification_date": raw_date,
            "download_url": download_url,
            "country": "Pakistan",
            "location": "Pakistan",
        }

        items.append(item)

    print(f"  SECP notifications: extracted {len(items)} items")
    return items


def _is_cloudflare_challenge(html: str) -> bool:
    if not html:
        return True
    lower = html.lower()
    return ("just a moment" in html and "challenge" in lower) or "cf-mitigated" in lower


def _secp_html_looks_valid(html: str) -> bool:
    if not html or _is_cloudflare_challenge(html):
        return False
    lower = html.lower()
    # Real page is large and contains a data table; CF interstitial is smaller / challenge text
    if "<table" not in lower:
        return False
    if len(html) < 20000 and ("cloudflare" in lower or "cf-" in lower):
        return False
    return True


async def scrape_secp_notifications_with_retry(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape SECP notifications with Cloudflare-aware strategy.

    Tested strategies (see test_cf_strategies.py):
      - BEST: wait_until=domcontentloaded + short settle delay (~43s success)
      - BAD:  wait_until=networkidle (timeouts)
      - BAD:  hard wait_for=css:table (often times out on CF challenge)
      - MIXED: long delay alone can return challenge HTML without a real table

    Approach:
      1) simple headless browser (stealth optional — baseline without stealth won tests)
      2) domcontentloaded (not networkidle)
      3) validate HTML (reject CF challenge pages)
      4) retry up to 3 times with cooldown breaks (15s / 30s / 45s)
      5) on later attempts, increase settle delay
    """
    url = url_config.get("url", "https://www.secp.gov.pk/laws/notifications/")
    if url.rstrip("/").endswith("/laws/notifications"):
        url = url.rstrip("/") + "/"

    print("  Detected SECP notifications — Cloudflare-aware scrape...")
    print(f"  URL: {url}")
    print("  Note: plain HTTP/Jina get 403; Gemini cannot bypass Cloudflare — need Chromium.")

    # Baseline profile matched the winning strategy test (A_baseline_domcontent)
    browser_cfg = BrowserConfig(
        headless=True,
        viewport_width=1366,
        viewport_height=768,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )

    max_attempts = 4
    cooldowns = [15, 30, 45, 60]  # seconds between attempts
    settle_delays = [4.0, 8.0, 12.0, 16.0]
    html_content = None
    last_error = None

    for attempt in range(1, max_attempts + 1):
        settle = settle_delays[attempt - 1]
        print(f"  SECP attempt {attempt}/{max_attempts} (domcontentloaded + {settle}s settle)...")
        # magic / simulate_user help some Cloudflare challenges when Chromium is installed
        run_kwargs = dict(
            word_count_threshold=1,
            remove_overlay_elements=True,
            screenshot=False,
            wait_for_images=False,
            cache_mode=CacheMode.BYPASS,
            page_timeout=120000,
            wait_until="domcontentloaded",
            delay_before_return_html=settle,
        )
        for extra in ("magic", "simulate_user", "override_navigator"):
            run_kwargs[extra] = True
        try:
            run_cfg = CrawlerRunConfig(**run_kwargs)
        except TypeError:
            # Older Crawl4AI without magic flags
            run_kwargs.pop("magic", None)
            run_kwargs.pop("simulate_user", None)
            run_kwargs.pop("override_navigator", None)
            run_cfg = CrawlerRunConfig(**run_kwargs)
        try:
            async with AsyncWebCrawler(config=browser_cfg, verbose=False) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

            if not result.success:
                last_error = result.error_message or "crawl failed"
                print(f"  ✗ Crawl failed: {last_error}")
            else:
                html_content = result.html or ""
                if _is_cloudflare_challenge(html_content):
                    last_error = "cloudflare_challenge_page"
                    print("  ✗ Got Cloudflare challenge page (not real content)")
                    html_content = None
                elif not _secp_html_looks_valid(html_content):
                    last_error = "html_missing_notifications_table"
                    print(f"  ✗ HTML fetched but notifications table not found (len={len(html_content)})")
                    # Soft fallback: still try extractor — sometimes headers differ
                    maybe = extract_secp_notifications(html_content, url_config)
                    if maybe:
                        print(f"  ✓ Extractor recovered {len(maybe)} items despite weak HTML heuristics")
                        return maybe
                    html_content = None
                else:
                    print(f"  ✓ Valid SECP HTML received ({len(html_content)} chars)")
                    break
        except Exception as e:
            last_error = str(e)
            print(f"  ✗ Exception: {last_error[:200]}")
            html_content = None

        if attempt < max_attempts:
            wait_s = cooldowns[attempt - 1]
            print(f"  ⏳ Cloudflare cooldown: waiting {wait_s}s before retry...")
            await asyncio.sleep(wait_s)

    if not html_content:
        print(f"✗ SECP scrape failed after {max_attempts} attempts (last={last_error})")
        print("  Tip: try again later; Cloudflare intermittently blocks headless browsers.")
        return []

    notifications = extract_secp_notifications(html_content, url_config)
    if notifications:
        print(f"✓ {url_config['name']}: Found {len(notifications)} notifications")
    else:
        print(f"⚠ {url_config['name']}: No notifications found in HTML")
    return notifications


def parse_gcf_datetime(value: str) -> Optional[datetime]:
    """Parse GCF Oracle dates like '10/9/26 6:00 PM' or '9/22/26 4:24 PM'."""
    if not value:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    for fmt in ("%m/%d/%y %I:%M %p", "%m/%d/%Y %I:%M %p", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def extract_gcf_negotiations(html: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract GCF Negotiation Abstracts rows from Oracle ADF HTML.

    Expected columns (order may vary; we map by header text):
    Negotiation | Title | Negotiation Type | Status | Posting Date | Open Date | Close Date | Details

    Keeps only Status == Active with Close Date on/after today.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    seen: set = set()

    # Prefer tables that look like the negotiations grid
    tables = soup.find_all("table")
    target_rows = []

    for table in tables:
        header_cells = []
        thead = table.find("thead")
        if thead:
            header_cells = thead.find_all(["th", "td"])
        if not header_cells:
            first_tr = table.find("tr")
            if first_tr:
                header_cells = first_tr.find_all(["th", "td"])
        headers = [c.get_text(" ", strip=True).lower() for c in header_cells]
        if not headers:
            continue
        if not (any("negotiation" in h for h in headers) and any("title" in h for h in headers)):
            continue
        if not any("status" in h or "close" in h for h in headers):
            # still accept if we see RFx pattern in body later
            pass

        # Map header index
        col = {}
        for i, h in enumerate(headers):
            if "negotiation" == h or h.startswith("negotiation") and "type" not in h:
                col.setdefault("negotiation", i)
            elif "title" in h:
                col.setdefault("title", i)
            elif "type" in h:
                col.setdefault("type", i)
            elif "status" in h:
                col.setdefault("status", i)
            elif "posting" in h:
                col.setdefault("posted", i)
            elif h.startswith("open") or "open date" in h:
                col.setdefault("open", i)
            elif "close" in h:
                col.setdefault("close", i)

        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 3:
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]
            # Skip pure header repeats
            joined = " ".join(texts).lower()
            if "negotiation type" in joined and "close date" in joined:
                continue

            def cell(key, default_idx=None):
                idx = col.get(key, default_idx)
                if idx is None or idx >= len(texts):
                    return ""
                return texts[idx]

            # Fallback positional layout from live page:
            # 0 Negotiation, 1 Title, 2 Type, 3 Status, 4 Posting, 5 Open, 6 Close
            negotiation = cell("negotiation", 0)
            title = cell("title", 1)
            neg_type = cell("type", 2)
            status = cell("status", 3)
            posted = cell("posted", 4)
            open_date = cell("open", 5)
            close_date = cell("close", 6)

            if not title or len(title) < 5:
                continue
            # Negotiation ids look like RFx202600043
            if negotiation and not re.search(r"RFx?\d|RFQ|RFP|RFI", negotiation, re.I):
                # maybe columns shifted — try find RFx in row
                for t in texts:
                    if re.match(r"RFx?\d", t, re.I):
                        negotiation = t
                        break

            status_l = status.lower().strip()
            if status_l and status_l != "active":
                continue

            close_dt = parse_gcf_datetime(close_date)
            if close_dt is None:
                # No usable deadline — skip (do not guess)
                continue
            if close_dt.replace(hour=0, minute=0, second=0, microsecond=0) < today:
                continue

            key = f"{negotiation}|{title}|{close_date}"
            if key in seen:
                continue
            seen.add(key)

            # Detail link if present
            link = url_config["url"]
            for a in tr.find_all("a", href=True):
                href = a.get("href", "").strip()
                if href and href not in ("#",) and "javascript:" not in href.lower():
                    if href.startswith("http"):
                        link = href
                    elif href.startswith("/"):
                        link = "https://iaayou.fa.ocs.oraclecloud.com" + href
                    break

            pub_iso = (parse_gcf_datetime(posted) or close_dt).isoformat()
            deadline_iso = close_dt.strftime("%Y-%m-%d")

            items.append({
                "id": generate_item_id(link + negotiation, title, pub_iso),
                "title": f"{negotiation}: {title}" if negotiation else title,
                "link": link,
                "description": f"{neg_type} | Status: {status} | Close: {close_date}",
                "content": "",
                "pubDate": pub_iso,
                "author": url_config.get("name", "Green Climate Fund"),
                "categories": [c for c in [neg_type, status, "GCF", "procurement"] if c],
                "source": {
                    "id": url_config["id"],
                    "name": url_config["name"],
                    "url": url_config["url"],
                },
                "image": None,
                "deadline": deadline_iso,
                "deadline_display": close_date,
                "reference_number": negotiation or None,
                "opportunity_type": neg_type or status or None,
                "posted": posted or None,
                "country": "Global",
                "location": "Global",
            })

    print(f"  GCF negotiations: extracted {len(items)} active open items")
    return items


async def scrape_gcf_negotiations_with_scroll(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scrape GCF Oracle ADF Negotiation Abstracts with scroll-to-load-more.

    Use a stable URL (prcBuId only). Session tokens in shared links expire.
    """
    # Strip volatile ADF session params if someone pasted a full browser URL
    raw_url = url_config.get("url", "")
    if "NegotiationAbstracts" in raw_url and "prcBuId=" in raw_url:
        m = re.search(r"(https?://[^?]+\?prcBuId=\d+)", raw_url)
        url = m.group(1) if m else raw_url.split("&_afrLoop")[0]
    else:
        url = raw_url

    print("  Detected GCF Negotiation Abstracts — browser scroll scrape...")
    print(f"  URL: {url}")

    browser_cfg = BrowserConfig(
        headless=True,
        viewport_width=1400,
        viewport_height=900,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )

    virtual_scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=25,
        scroll_by="page_height",
        wait_after_scroll=1.5,
    )

    run_cfg = CrawlerRunConfig(
        word_count_threshold=5,
        remove_overlay_elements=True,
        screenshot=False,
        wait_for_images=False,
        cache_mode=CacheMode.BYPASS,
        page_timeout=180000,
        wait_until="domcontentloaded",
        delay_before_return_html=5.0,
        virtual_scroll_config=virtual_scroll_config,
        scan_full_page=True,
    )

    try:
        async with AsyncWebCrawler(config=browser_cfg, verbose=False) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            if not result.success:
                print(f"✗ GCF crawl failed: {result.error_message}")
                return []
            html_content = result.html or ""
            print(f"  HTML length after scroll: {len(html_content)}")
    except Exception as e:
        print(f"✗ GCF crawl exception: {e}")
        return []

    if not html_content or len(html_content) < 1000:
        print("⚠ GCF page HTML too small / empty")
        return []

    # Soft check we got negotiation content
    if "RFx" not in html_content and "Negotiation" not in html_content:
        print("⚠ GCF HTML missing expected negotiation markers")

    items = extract_gcf_negotiations(html_content, url_config)
    if items:
        print(f"✓ {url_config['name']}: Found {len(items)} active open negotiations")
    else:
        print(f"⚠ {url_config['name']}: No active open negotiations found")
    return items


def parse_undp_deadline_date(value: str) -> Optional[datetime]:
    """Parse UNDP deadline/posted datetime strings to datetime (date portion)."""
    if not value:
        return None
    value = str(value).strip()
    candidates = [
        value[:26] if "." in value else None,  # with microseconds
        value[:19] if " " in value else None,  # YYYY-MM-DD HH:MM:SS
        value[:10] if len(value) >= 10 and value[4] == "-" else None,  # YYYY-MM-DD
        value,
    ]
    formats = (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%b-%y",
        "%d-%b-%Y",
    )
    for candidate in candidates:
        if not candidate:
            continue
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    return None


def extract_undp_pakistan_notices(js_payload: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse UNDP Pakistan procurement notices from the public-components JS payload.
    Source: https://public-components.undp.org/?comp=proc_notices&cty_id_c=PAK&style_type=table
    Keeps only notices whose deadline is still active (deadline date >= today).
    """
    import json
    from datetime import date

    start = js_payload.find('{"recordcount"')
    if start < 0:
        print("⚠ UNDP component payload: no recordcount JSON found")
        return []

    try:
        payload, _ = json.JSONDecoder().raw_decode(js_payload[start:])
    except json.JSONDecodeError as e:
        print(f"⚠ UNDP component JSON parse failed: {e}")
        return []

    recordcount = int(payload.get("recordcount") or 0)
    data = payload.get("data") or {}
    if recordcount <= 0 or not data:
        print("⚠ UNDP: no procurement notices in payload")
        return []

    today = date.today()
    items: List[Dict[str, Any]] = []
    skipped_expired = 0

    for i in range(recordcount):
        try:
            title = (data.get("title") or [None] * recordcount)[i] or "UNDP Procurement Notice"
            development_area = (data.get("area_desc") or [""] * recordcount)[i] or ""
            location = (data.get("duty_station") or [""] * recordcount)[i] or ""
            # Prefer country short text when present
            cty = (data.get("cty_sht_t") or data.get("duty_station_cty") or [""] * recordcount)
            country_label = cty[i] if i < len(cty) else ""
            if country_label and location and country_label.upper() not in location.upper():
                location_display = f"{location}, {country_label}"
            else:
                location_display = location or country_label or "Pakistan"

            reference_number = (data.get("notice_id") or [""] * recordcount)[i] or ""
            posted_fmt = (data.get("formatted_post_date") or [""] * recordcount)[i] or ""
            deadline_fmt = (data.get("formatted_date") or [""] * recordcount)[i] or ""
            posted_raw = (data.get("posted_d") or [""] * recordcount)[i] or ""
            deadline_raw = (data.get("deadline") or data.get("date") or [""] * recordcount)[i] or ""
            view_link = (data.get("link") or [""] * recordcount)[i] or url_config.get("url")

            deadline_dt = parse_undp_deadline_date(str(deadline_raw) if deadline_raw else deadline_fmt)
            if not deadline_dt:
                print(f"  ⚠ Skipping UNDP row without parseable deadline: {title[:60]}")
                continue

            # Active = deadline date is today or in the future
            if deadline_dt.date() < today:
                skipped_expired += 1
                continue

            posted_dt = parse_undp_deadline_date(str(posted_raw) if posted_raw else posted_fmt)
            pub_iso = posted_dt.isoformat() if posted_dt else datetime.now().isoformat()
            deadline_iso = deadline_dt.strftime("%Y-%m-%d")

            description = (
                f"Development Area: {development_area}\n"
                f"Title: {title}\n"
                f"Location: {location_display}\n"
                f"Reference Number: {reference_number}\n"
                f"Posted: {posted_fmt or (posted_dt.strftime('%d-%b-%y') if posted_dt else '')}\n"
                f"Deadline: {deadline_fmt or deadline_dt.strftime('%d-%b-%y')}"
            )

            items.append({
                "id": generate_item_id(view_link or reference_number, title, deadline_iso),
                "title": title,
                "link": view_link,  # Direct notice View page (not listing page)
                "description": description,
                "content": description,
                "pubDate": pub_iso,
                "deadline": deadline_iso,
                "author": url_config.get("name", "UNDP Pakistan"),
                "categories": [
                    "procurement",
                    "undp",
                    "pakistan",
                    "tender",
                    development_area.lower() if development_area else "other",
                ],
                "source": {
                    "id": url_config["id"],
                    "name": url_config["name"],
                    "url": url_config["url"],
                },
                "image": None,
                "development_area": development_area,
                "location": location_display,
                "reference_number": reference_number,
                "posted": posted_fmt or (posted_dt.strftime("%d-%b-%y") if posted_dt else ""),
                "deadline_display": deadline_fmt or deadline_dt.strftime("%d-%b-%y"),
                "opportunity_type": "Tender",
                "attachments": [{"name": "View", "url": view_link}] if view_link else [],
            })
        except Exception as e:
            print(f"  ⚠ Skipping UNDP row {i}: {e}")
            continue

    print(
        f"  UNDP Pakistan: kept {len(items)} active notice(s), "
        f"skipped {skipped_expired} expired (as of {today.isoformat()})"
    )
    return items


async def scrape_undp_pakistan_procurement(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch UNDP Pakistan procurement notices via the public-components feed
    (same data the website table uses), filter to active deadlines only.
    """
    component_url = (
        "https://public-components.undp.org/"
        "?comp=proc_notices&cty_id_c=PAK&style_type=table"
    )
    print("  Detected UNDP Pakistan procurement — fetching notices component...")
    print(f"  Component URL: {component_url}")

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Referer": url_config.get("url", "https://www.undp.org/pakistan/procurement"),
        }
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(component_url)
            resp.raise_for_status()
            payload = resp.text
    except Exception as e:
        print(f"✗ Error fetching UNDP procurement component: {e}")
        return []

    notices = extract_undp_pakistan_notices(payload, url_config)
    if notices:
        print(f"✓ {url_config['name']}: Found {len(notices)} active notices")
    else:
        print(f"⚠ {url_config['name']}: No active notices found")
    return notices


def _parse_propakistani_date_text(text: str) -> Optional[datetime]:
    """Parse dates like 'Oct 5, 2026 | 10:21 am' or '10:21 am | Oct 5, 2026'."""
    if not text:
        return None
    text = text.strip()
    patterns = [
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})",
        r"(\d{1,2})-(\d{1,2})-(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        if pattern.startswith("(Jan"):
            month_str, day_str, year_str = match.groups()
            try:
                return datetime.strptime(f"{month_str} {day_str} {year_str}", "%b %d %Y")
            except ValueError:
                continue
        day_str, month_str, year_str = match.groups()
        try:
            return datetime(int(year_str), int(month_str), int(day_str))
        except ValueError:
            continue
    lowered = text.lower()
    now = datetime.now()
    if any(k in lowered for k in ("just now", "minute ago", "hour ago", "today")):
        return now
    if "yesterday" in lowered or re.search(r"\b1 day ago\b", lowered):
        return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    day_ago = re.search(r"(\d+)\s+days?\s+ago", lowered)
    if day_ago:
        return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int(day_ago.group(1)))
    return None


def _propakistani_article_blocks(soup: BeautifulSoup) -> List[Any]:
    """Find listing blocks on ProPakistani category pages."""
    blocks = soup.find_all("article")
    if not blocks:
        blocks = soup.select('div[class*="post"], div[class*="story"], div[class*="article"]')
    if not blocks:
        blocks = [
            h for h in soup.find_all(["h2", "h3", "h4", "h5"])
            if h.find("a", href=True)
        ]
    return blocks


def extract_propakistani_articles(html: str, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract recent articles from ProPakistani Business category page.
    Includes items from the last few days (site shows dates like 'Oct 5, 2026 | 10:21 am').
    """
    max_days = int(url_config.get("max_age_days", 7))
    cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=max_days)
    articles: List[Dict[str, Any]] = []
    seen_links: set = set()

    try:
        soup = BeautifulSoup(html, "html.parser")
        article_elements = _propakistani_article_blocks(soup)
        print(f"  Found {len(article_elements)} ProPakistani listing blocks")

        for article_elem in article_elements:
            try:
                title_tag = article_elem.find(["h2", "h3", "h4", "h5", "a"])
                if not title_tag:
                    continue
                title = title_tag.get_text().strip()
                if not title or len(title) < 8:
                    continue

                link_tag = article_elem.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag.get("href", "").strip()
                if not link or "/category/" in link or "/tag/" in link or "/author/" in link:
                    continue
                if link.startswith("/"):
                    link = "https://propakistani.pk" + link
                elif not link.startswith("http"):
                    link = "https://propakistani.pk/" + link
                if link in seen_links:
                    continue

                block_text = article_elem.get_text(" ", strip=True)
                parent_text = ""
                parent = article_elem.parent
                for _ in range(3):
                    if parent is None:
                        break
                    parent_text = parent.get_text(" ", strip=True)
                    if re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}", parent_text, re.I):
                        break
                    parent = parent.parent

                date_text = block_text if re.search(r"\d{4}", block_text) else parent_text
                parsed_date = _parse_propakistani_date_text(date_text)
                if parsed_date and parsed_date.replace(hour=0, minute=0, second=0, microsecond=0) < cutoff:
                    continue
                if not parsed_date:
                    # No date found — skip (do not guess)
                    continue

                description = ""
                desc_elem = article_elem.find("p")
                if desc_elem:
                    description = desc_elem.get_text().strip()[:300]

                image = ""
                img_elem = article_elem.find("img")
                if img_elem:
                    image = img_elem.get("src") or img_elem.get("data-src") or ""
                    if image.startswith("/"):
                        image = "https://propakistani.pk" + image

                pub_date = parsed_date.isoformat()
                seen_links.add(link)
                articles.append({
                    "id": generate_item_id(link, title, pub_date),
                    "title": title,
                    "link": link,
                    "description": description,
                    "content": description,
                    "pubDate": pub_date,
                    "author": url_config.get("name", "ProPakistani"),
                    "categories": ["Pakistan", "Business"],
                    "source": {
                        "id": url_config["id"],
                        "name": url_config["name"],
                        "url": url_config["url"],
                    },
                    "image": image or None,
                    "country": "Pakistan",
                    "location": "Pakistan",
                })
                print(f"  ✓ ProPakistani: {title[:70]}...")
            except Exception as e:
                print(f"  ⚠ Error processing ProPakistani block: {e}")
                continue

        print(f"  Total ProPakistani articles (last {max_days} days): {len(articles)}")
        return articles

    except Exception as e:
        print(f"  ✗ Error extracting ProPakistani articles: {str(e)}")
        return []


async def scrape_single_url(url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scrape a single URL using Crawl4ai and extract relevant content"""
    try:
        url = url_config['url']
        print(f"Scraping: {url_config['name']}...")
        print(f"  URL: {url}")
        
        keywords = url_config.get('keywords', [])
        scraped_items = []

        # UNDP Pakistan procurement — JSON feed via public-components (no browser needed)
        if "undp.org" in url.lower() and "procurement" in url.lower():
            return await scrape_undp_pakistan_procurement(url_config)

        # SECP — Cloudflare-protected; dedicated retry/cooldown strategy
        if "secp.gov.pk" in url.lower():
            return await scrape_secp_notifications_with_retry(url_config)

        # GCF Oracle ADF negotiations — scroll to load more; filter Active + open deadline
        if "oraclecloud.com" in url.lower() and "negotiationabstracts" in url.lower():
            return await scrape_gcf_negotiations_with_scroll(url_config)
        if url_config.get("id") == "gcf-negotiations":
            return await scrape_gcf_negotiations_with_scroll(url_config)

        # PakTender — plain HTTP table (pages 1–2); skip keyword filter in dedicated path
        if "paktender.com" in url.lower() or url_config.get("id") == "paktender":
            return await scrape_paktender_pages(url_config)

        # UNGM — JS table needs browser scroll; dedicated path (not generic Crawl4AI first)
        if "ungm.org" in url.lower() or url_config.get("id") == "ungm":
            return await scrape_ungm_with_scroll(url_config)

        html_content = None

        # Default: use Crawl4AI for dynamic sites
        crawler_config = CrawlerRunConfig(
            word_count_threshold=10,  # Minimum words to consider content
            remove_overlay_elements=True,  # Remove popups, modals, etc.
            screenshot=False,
            wait_for_images=False,
            cache_mode=CacheMode.BYPASS,  # Use CacheMode instead of deprecated bypass_cache
        )

        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )
                
                if not result.success:
                    print(f"✗ Error scraping {url_config['name']}: {result.error_message}")
                    return []
                html_content = result.html
                
        except Exception as e:
            print(f"✗ Crawl4ai error for {url_config['name']}: {str(e)}")
            return []

        if html_content is None:
            return []

        # Cloudflare challenge page = not real content
        if _is_cloudflare_challenge(html_content):
            print("✗ Cloudflare challenge blocked the scrape.")
            return []
        
        # Extract meta information (for non-table pages)
        meta_info = extract_meta_info(html_content)
        
        # Get title
        title = meta_info.get('title', '')
        if not title:
            # Try to extract from HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('title') or soup.find('h1')
            if title_tag:
                title = title_tag.get_text().strip()
        
        if not title:
            title = url_config.get('name', 'Untitled')
        
        # Extract description
        description = meta_info.get('description', '')
        if not description:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Try meta description, then first p tag
            desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if desc_tag:
                description = desc_tag.get('content', '')
            else:
                first_p = soup.find('p')
                if first_p:
                    description = first_p.get_text().strip()[:500]  # First 500 chars
        
        # Extract main content
        content = extract_text_from_html(html_content)
        
        # Extract images
        images = extract_images_from_html(html_content)
        main_image = meta_info.get('image') or (images[0] if images else None)
        
        # Create item
        pub_date = datetime.now().isoformat()  # Use current date for scraped content
        
        item = {
            "id": generate_item_id(url, title, pub_date),
            "title": title,
            "link": url,
            "description": description[:500] if description else "",  # Limit description length
            "content": content[:5000] if content else "",  # Limit content length
            "pubDate": pub_date,
            "author": url_config.get('name', 'Unknown'),
            "categories": [],
            "source": {
                "id": url_config["id"],
                "name": url_config["name"],
                "url": url_config["url"]
            },
            "image": main_image
        }
        
        # Filter for relevant content
        if filter_relevant_content(item, keywords):
            scraped_items.append(item)
            print(f"✓ {url_config['name']}: Found 1 relevant item")
        else:
            print(f"⚠ {url_config['name']}: Content not relevant (filtered out)")
        
        return scraped_items
        
    except Exception as error:
        print(f"✗ Error scraping {url_config['name']}: {str(error)}")
        return []
        
        return scraped_items
        
    except Exception as error:
        print(f"✗ Error scraping {url_config['name']}: {str(error)}")
        return []


async def scrape_multiple_urls(url_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scrape multiple URLs concurrently
    
    Args:
        url_configs: List of URL configuration dictionaries
        
    Returns:
        List of scraped and filtered items, sorted by date (newest first)
    """
    # Scrape all URLs concurrently
    tasks = [scrape_single_url(url_config) for url_config in url_configs]
    results = await asyncio.gather(*tasks)
    
    # Flatten all items into a single list
    all_items = []
    for items in results:
        all_items.extend(items)
    
    # Sort by publication date (newest first)
    all_items.sort(
        key=lambda x: x.get('pubDate', ''),
        reverse=True
    )
    
    return all_items
