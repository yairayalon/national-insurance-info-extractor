# National Insurance Form Processor

A comprehensive system for extracting structured data from Israeli National Insurance (ביטוח לאומי) forms using Azure Document Intelligence OCR and Azure OpenAI GPT-4o.

## Overview

This project processes filled National Insurance form 283 (בקשה למתן טיפול רפואי לנפגע עבודה - עצמאי) and extracts all relevant information into structured JSON format. The system handles Hebrew and English text, validates extracted data, and provides a user-friendly web interface.

## Features

- **OCR Processing**: Azure Document Intelligence for accurate text extraction from PDF/image files
- **AI-Powered Extraction**: GPT-4o for intelligent field identification and data normalization
- **Multi-language Support**: Handles forms filled in Hebrew or English
- **Data Validation**: Comprehensive validation with accuracy and completeness scoring
- **Web Interface**: Streamlit-based UI for easy file upload and result visualization
- **Structured Output**: JSON format matching the required schema
- **Error Handling**: Robust error handling and logging throughout the pipeline

## Architecture

The system follows a modular architecture:

```
national-insurance-info-extractor/
├── main.py                  # Main application entry point
├── README.md                # Project documentation
├── requirements.txt         # Dependencies
├── .env.example             # Environment variables template
├── modules/                 # Core processing modules
│   ├── config_loader.py     # Load configuration and schemas
│   ├── field_validator.py   # Validate extracted fields
│   ├── ocr_processor.py     # OCR extraction logic
│   └── __init__.py
├── ui/                      # User interface
│   └── streamlit_app.py     # Streamlit front-end
└── config/                  # Schema definitions
    ├── schema_english.json
    └── schema_hebrew.json
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yairayalon/national-insurance-info-extractor.git
   cd national-insurance-info-extractor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your Azure credentials:
   ```env
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-document-intelligence-resource.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=your-document-intelligence-api-key-here
   AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
   AZURE_OPENAI_KEY=your-azure-openai-api-key-here
   AZURE_OPENAI_MODEL=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

## Usage

### Web Interface (Recommended)

Launch the Streamlit application:
```bash
streamlit run ui/streamlit_app.py
```

1. Open your browser to `http://localhost:8501`
2. Upload a PDF or image file containing a filled National Insurance form
3. Click "Process Form" to extract data
4. View results in organized tabs and download JSON output

### Command Line Interface

Process a single form:
```bash
python main.py path/to/form.pdf
```

Save output to file:
```bash
python main.py path/to/form.pdf --output extracted_data.json
```

Enable verbose logging:
```bash
python main.py path/to/form.pdf --verbose
```

## Data Validation

The system includes comprehensive validation:

- **Completeness Score**: Percentage of fields successfully extracted
- **OCR Confidence**: Average confidence score from Document Intelligence
- **Format Validation**: ID numbers, phone numbers, date formats
- **Empty Field Detection**: Lists fields that couldn't be extracted
- **Warnings**: Alerts for potential data quality issues

## Key Components

### FormProcessor (`main.py`)
- Core orchestration class
- Integrates OCR, GPT extraction, and validation
- Handles error recovery and logging

### OCRProcessor (`modules/ocr_processor.py`)
- Azure Document Intelligence integration
- Multiple fallback configurations for robust processing
- Structured data extraction (text, tables, checkboxes)

### Field Extraction (GPT-4o)
- Intelligent prompt engineering for Hebrew/English forms
- OCR artifact cleaning (e.g., correcting "85" → "05" in phone numbers)
- Context-aware field identification
- Schema compliance enforcement

### FieldValidator (`modules/field_validator.py`)
- Completeness and accuracy scoring
- Format validation for ID numbers, phones, dates
- Warning generation for potential issues

## Technical Considerations

### OCR Challenges Handled
- Mixed Hebrew/English text
- Handwritten vs. printed text distinction
- OCR artifacts and corrections
- Form structure recognition

### AI Prompt Engineering
- Detailed system prompts for accurate extraction
- Field-specific validation rules
- Context preservation for ambiguous cases
- Robust error handling for malformed responses