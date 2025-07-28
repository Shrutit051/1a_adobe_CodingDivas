# PDF Heading Extractor

A Python-based utility for extracting structured heading hierarchies and outlines from PDF documents using PyMuPDF. The tool intelligently detects headings (H1, H2, H3) by analyzing font size, weight, and layout features—and optionally extracts the corresponding section text.

---

## Table of Contents

- [Getting Started (Docker)](#getting-started-docker)
  - [1. Build the Docker Image](#1-build-the-docker-image)
  - [2. Prepare Input Files](#2-prepare-input-files)
  - [3. Run the Container](#3-run-the-container)
  - [4. Locate Output Files](#4-locate-output-files)
- [Overview](#overview)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Diagram](#diagram)
- [Output Format](#output-format)

---

## Getting Started (Docker)

### 1. Build the Docker Image

Navigate to your project directory and run the following command to build the Docker image:

```bash
docker build -t pdf-heading-extractor .
```

## 2. Prepare Input Files
Place your PDF documents into a local folder, for example: ./input.

## 3. Run the Container
Execute the container with appropriate volume mounts for input and output:

```
docker run --rm -v /input:/app/input -v /output:/app/output pdf-heading-extractor
```
All .pdf files in the /input directory will be processed.
Corresponding .json outline files will be saved to the /output directory.

Note:
Inside the container, /app/input and /app/output are the working directories.
Make sure your local /input folder contains valid PDFs before running the container.

## 4. Locate Output Files
Once processing completes, check your specified /output directory for generated .json files.

## Overview
Many PDFs lack semantic metadata or consistent formatting for heading detection. This tool reconstructs logical document structure by analyzing text spans based on font size, boldness, indentation, and vertical spacing.
It categorizes headings into hierarchical levels (H1, H2, H3) and can optionally associate body text under each heading, making it suitable for tasks such as summarization, indexing, or semantic search.

## How It Works
Text Span Extraction
Each page is parsed using PyMuPDF, extracting spans with metadata such as font size, position, and boldness.

Noise Filtering
Non-informative content—like repeated header lines, decorative symbols, or overly short text—is ignored.

Font Weight Adjustment
Bolded spans are given a slight boost in effective font size to better distinguish headings.

Dynamic Layout Thresholds
The script calculates median indentation and vertical spacing to tune heading detection thresholds per document.

Heading Level Mapping
The top three largest unique font sizes are mapped to H1, H2, and H3 levels respectively.

Outline Construction
Text spans with similar styles and proximity are grouped and merged to form complete headings. A hierarchical outline is then constructed.

(Optional) Section Text Extraction
When enabled, paragraph text below each heading is also captured and associated with that heading in the output.

## Project Structure
```
/app
│
├── extract_headings.py        # Core logic for heading extraction
├── process_pdfs.py            # Batch processor for all input PDFs
├── requirements.txt           # Python package requirements
├── Dockerfile                 # Docker image configuration
├── input/                     # Directory for input PDF files
└── output/                    # Directory for output JSON results
```

```
{
  "title": "Sample Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Introduction",
      "page": 1
    },
    {
      "level": "H2",
      "text": "Background",
      "page": 2
    }
  ]
}
```
