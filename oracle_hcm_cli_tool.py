#!/usr/bin/env python3

import argparse
import json
import re
import time
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/"

def extract_links_from_toc(toc_file: Path, output_csv: Path):
    js_content = toc_file.read_text(encoding="utf-8")
    matches = re.findall(
        r'\{[^{}]*"title"\s*:\s*"([^"]+)"[^{}]*"href"\s*:\s*"([^"]+)"[^{}]*\}', js_content)

    links = []
    for title, href in matches:
        href_clean = href.split("#")[0].strip()
        full_url = BASE_URL + href_clean
        links.append({"name": title.strip(), "url": full_url})

    df = pd.DataFrame(links)
    df.to_csv(output_csv, index=False)
    print(f"✅ Extracted {len(links)} links to {output_csv}")

def convert_csv_to_json(csv_file: Path, json_file: Path):
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.lower()
    df.to_json(json_file, orient="records", indent=2)
    print(f"✅ Converted CSV to JSON at {json_file}")

def extract_metadata_from_links(json_file: Path, tables_output: Path, views_output: Path):
    with open(json_file, "r", encoding="utf-8") as f:
        table_links = json.load(f)

    def extract_object_metadata(page, url, name):
        page.goto(url)
        page.wait_for_timeout(2000)
        soup = BeautifulSoup(page.content(), "html.parser")

        title_tag = soup.find(["h1", "h2"])
        object_name = title_tag.text.strip() if title_tag else name

        # Description
        description = ""
        body_div = soup.find("div", class_="body")
        if body_div:
            for p in body_div.find_all("p", recursive=False):
                text = p.get_text(strip=True)
                if text:
                    description = text
                    break

        # Details
        details = ""
        object_type = "TABLE"  # default
        details_section = soup.find("h2", string=re.compile("Details", re.I))
        if details_section:
            lines = []
            for sibling in details_section.find_next_siblings():
                if sibling.name == "h2":
                    break
                if sibling.name in ["p", "ul", "li"]:
                    text = sibling.get_text(" ", strip=True)
                    if text:
                        lines.append(text)
                        match = re.search(r"Object type:\s*(\w+)", text, re.I)
                        if match:
                            object_type = match.group(1).strip().upper()
            details = " ".join(lines)
            details = re.sub(r"(?<=[a-zA-Z])(?=Object)", " ", details).strip()

        # Columns
        columns = []
        columns_section = soup.find("h2", string=re.compile("Columns", re.I))
        if columns_section:
            table_tag = columns_section.find_next("table")
            if table_tag:
                if object_type == "VIEW":
                    td = table_tag.find("td")
                    if td:
                        for p in td.find_all("p"):
                            col_name = p.get_text(strip=True)
                            if col_name:
                                columns.append({"column_name": col_name})
                else:  # TABLE
                    for row in table_tag.find_all("tr")[1:]:
                        cells = row.find_all("td")
                        if len(cells) >= 6:
                            columns.append({
                                "column_name": cells[0].text.strip(),
                                "data_type": cells[1].text.strip(),
                                "length": cells[2].text.strip(),
                                "precision": cells[3].text.strip(),
                                "not_null": cells[4].text.strip().lower() == "yes",
                                "description": cells[5].text.strip()
                            })

        # Views
        if object_type == "VIEW":
            sql_query = ""
            query_section = soup.find("h2", string=re.compile("Query", re.I))
            if query_section:
                query_table = query_section.find_next("table")
                if query_table:
                    sql_query = "\n".join(p.get_text(strip=True) for p in query_table.find_all("p"))

            return {
                "view_name": object_name,
                "url": url,
                "description": description,
                "details": details,
                "columns": columns,
                "sql_query": sql_query
            }

        # Tables
        primary_key = {}
        pk_section = soup.find("h2", string=re.compile("Primary Key", re.I))
        if pk_section:
            pk_table = pk_section.find_next("table")
            if pk_table and len(pk_table.find_all("tr")) > 1:
                pk_row = pk_table.find_all("tr")[1]
                cells = pk_row.find_all("td")
                if len(cells) == 2:
                    primary_key = {
                        "name": cells[0].text.strip(),
                        "columns": [col.strip() for col in cells[1].text.strip().split(",")]
                    }

        indexes = []
        index_section = soup.find("h2", string=re.compile("Indexes", re.I))
        if index_section:
            index_table = index_section.find_next("table")
            for row in index_table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    indexes.append({
                        "name": cells[0].text.strip(),
                        "uniqueness": cells[1].text.strip(),
                        "columns": [col.strip() for col in cells[3].text.strip().split(",")]
                    })

        return {
            "table_name": object_name,
            "url": url,
            "description": description,
            "details": details,
            "columns": columns,
            "primary_key": primary_key,
            "indexes": indexes
        }

    tables = []
    views = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, entry in enumerate(table_links):
            try:
                print(f"🔍 {i+1}/{len(table_links)}: {entry['name']}")
                metadata = extract_object_metadata(page, entry["url"], entry["name"])
                if "view_name" in metadata:
                    views.append(metadata)
                else:
                    tables.append(metadata)
            except Exception as e:
                print(f"⚠️ Error with {entry['url']}: {e}")
            time.sleep(1.0)

        browser.close()

    with open(tables_output, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2)
    print(f"✅ Saved metadata for {len(tables)} tables → {tables_output}")

    with open(views_output, "w", encoding="utf-8") as f:
        json.dump(views, f, indent=2)
    print(f"✅ Saved metadata for {len(views)} views → {views_output}")

def main():
    parser = argparse.ArgumentParser(description="Oracle HCM CLI Tool")
    parser.add_argument("--toc", type=Path, help="Path to toc.js file")
    parser.add_argument("--csv", type=Path, help="Output CSV file path")
    parser.add_argument("--json", type=Path, help="Output JSON file path (converted from CSV)")
    parser.add_argument("--tables", type=Path, help="Output JSON file for tables")
    parser.add_argument("--views", type=Path, help="Output JSON file for views")

    args = parser.parse_args()

    if args.toc and args.csv:
        extract_links_from_toc(args.toc, args.csv)

    if args.csv and args.json:
        convert_csv_to_json(args.csv, args.json)

    if args.json and args.tables and args.views:
        extract_metadata_from_links(args.json, args.tables, args.views)

if __name__ == "__main__":
    main()