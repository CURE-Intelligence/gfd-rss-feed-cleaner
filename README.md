# RSS Feed Cleaner

This project fetches multiple RSS feeds, filters out already seen items, and generates clean RSS XML files for each feed. The RSS files are stored in the `feeds/` folder and are ready to be published via GitHub Pages.

---

## Features

- Keeps track of seen items using separate JSON files for each feed.
- Generates clean RSS XML files per feed.
- Automated updates via GitHub Actions.
- Ready to serve via GitHub Pages for external tools.

---

## Setup Instructions

1. Clone this repository:

    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2. Create a virtual environment:

    ```bash
    python3 -m venv venv
    ```

3. Activate the virtual environment:

    - Windows: `venv\Scripts\activate`
    - Linux/macOS: `source venv/bin/activate`

4. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

---

## Running the Project

- To fetch and generate RSS files for all feeds:

    ```bash
    python main.py
    ```

- The generated XML files will be saved in the `feeds/` folder.

---

## GitHub Actions

The repository is configured with GitHub Actions to automatically:

- Run the script on a schedule.
- Commit and push updated RSS XML and seen IDs back to the repository.

---

## GitHub Pages

- The `feeds/` folder can be served via GitHub Pages.
- Each XML file will have its own URL.

---

## Notes

- Each feed keeps its own JSON file to track which items have already been processed.

---
