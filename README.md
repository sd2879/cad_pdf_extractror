# CAD PDF Extractor

This project is a web application that allows users to upload PDF files, view and extract specific sections using bounding boxes, and process images with OCR. The application is built with Flask and utilizes PyMuPDF for PDF handling, PaddleOCR for text extraction, and OpenCV for image processing.

## Features

- **PDF Upload and Viewing**: Upload PDF files and navigate through pages to view and select specific regions.
- **Bounding Box Extraction**: Extract images within specified bounding boxes on any PDF page.
- **OCR Text Extraction**: Extract text from images within bounding boxes using PaddleOCR.
- **Data Persistence**: Save and manage extracted data in JSON format for each PDF file.

## Project Structure

cad_pdf_extractor/
├── app.py                 # Main Flask application
├── ocr.py                 # OCR processing module
├── requirements.txt       # Dependency list
├── templates/             # HTML templates
│   ├── upload.html        # Upload page
│   └── index.html         # Main interface
├── static/                # Static files (CSS, JS, images)
│   └── css/
│       └── styles.css     # Stylesheet (if applicable)
├── data/                  # Data storage
│   ├── pdf/               # Uploaded PDFs
│   └── instance/          # Extracted JSON data
└── assets/                # Media assets (demo GIFs, screenshots)

## Prerequisites

Ensure you have Python installed on your system. You will also need to install dependencies listed in the `requirements.txt` file.

## Installation

1. Clone this repository to your local machine.
2. Navigate to the project directory:

    ```bash
    cd cad_pdf_extractor
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Run the Flask application:

    ```bash
    python app.py
    ```

2. Open a web browser and go to `http://127.0.0.1:5000` to access the application.
3. Upload a PDF file and use the interface to navigate through pages, extract bounding boxes, and process OCR.

## Dependencies

The application requires the following main dependencies:

- Flask
- PyMuPDF
- PaddleOCR
- OpenCV

For the full list, refer to `requirements.txt`.

## License

This project is open source, just for you!

