````markdown
# Oracle HCM Documentation Scraping CLI Tool

This command-line utility automates the extraction of **table** and **view** metadata from the Oracle Cloud HCM documentation site to be used for downstream purposes.

## Features

- 🔗 Extract table and view links from a downloaded `toc.js` file
- 🔄 Convert link CSV to JSON
- 📦 Scrape detailed metadata for **Tables** and **Views**, including:
  - For **Tables**: column names, data types, lengths, precisions, nullability, descriptions, primary keys, indexes, and additional details
  - For **Views**: only column names and the full SQL definition

## Requirements

```bash
pip install pandas beautifulsoup4 playwright
playwright install
````

## Usage

### Step 1: Extract links from `toc.js` into CSV

```bash
python oracle_hcm_cli_tool.py --toc toc.js --csv oracle_links.csv
```

### Step 2: Convert CSV to JSON

```bash
python oracle_hcm_cli_tool.py --csv oracle_links.csv --json oracle_links.json
```

### Step 3: Extract metadata for both Tables and Views

```bash
python oracle_hcm_cli_tool.py --json oracle_links.json --tables oracle_tables.json --views oracle_views.json
```

### Run all steps in one command:

```bash
python oracle_hcm_cli_tool.py --toc toc.js --csv oracle_links.csv --json oracle_links.json --tables oracle_tables.json --views oracle_views.json
```

## Output Format

### 🧾 Table JSON (`oracle_tables.json`)

* Uses the `"table_name"` field
* Includes:

  * `columns`: full metadata (name, type, length, precision, nullability, description)
  * `primary_key`: name and column(s)
  * `indexes`: name, uniqueness, and columns
  * `description` and `details`

### 👓 View JSON (`oracle_views.json`)

* Uses the `"view_name"` field
* Includes:

  * `columns`: only the `column_name`
  * `sql_query`: full SQL definition
  * `description` and `details`

## Notes

* Views are **no longer identified by `_VL` suffix**. Instead, the tool inspects the **"Object type"** in the Details section to determine whether an object is a Table or View.
* Be sure to use the actual `toc.js` file from Oracle’s documentation site.
* Output files are in standard `.csv` and `.json` formats and are suitable for automation or reporting pipelines.

> **Disclaimer:**  

> This tool and blog post are independently created for research, education, and internal productivity enhancement by an Oracle customer.
> All references to Oracle® products and documentation are made strictly for educational and interoperability purposes.  
> Oracle, Java, and MySQL are registered trademarks of Oracle and/or its affiliates.  
> This tool is **not affiliated with or sponsored by Oracle Corporation**.  
>  
> Metadata shown (such as table/view names, columns, and SQL definitions) are extracted from publicly accessible Oracle documentation for the purpose of learning, automation, and support.  
> No proprietary Oracle documentation or content is redistributed or republished in full.  
>  
> Always refer to [Oracle Cloud Documentation](https://docs.oracle.com/en/cloud/saas/human-resources/oedmh/) for official and up-to-date information.

```
