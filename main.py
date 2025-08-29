import json
import logging
from typing import Dict, Any
from openai import AzureOpenAI

from modules.config_loader import ConfigLoader
from modules.ocr_processor import OCRProcessor
from modules.field_validator import FieldValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FormProcessor:
    def __init__(self):
        # Load configuration
        self.config = ConfigLoader()

        # Initialize OCR processor
        self.ocr = OCRProcessor(
            endpoint=self.config.get('doc_intelligence.endpoint'),
            key=self.config.get('doc_intelligence.key')
        )

        # Initialize GPT client for extraction
        self.gpt_client = AzureOpenAI(
            azure_endpoint=self.config.get('openai.endpoint'),
            api_key=self.config.get('openai.key'),
            api_version=self.config.get('openai.api_version')
        )
        self.gpt_model = self.config.get('openai.model')

        # Initialize validator
        self.validator = FieldValidator()

    def process_form(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single form through the complete pipeline

        Args:
            file_path: Path to PDF/image file

        Returns:
            Dictionary with extracted data and validation results
        """
        logger.info(f"Processing form: {file_path}")

        try:
            # Step 1: OCR Processing
            logger.info("Running OCR...")
            ocr_result = self.ocr.process_document(file_path)

            # Step 2: Extract and normalize with GPT-4o
            logger.info("Extracting fields with GPT-4o...")
            extracted_data = self._extract_with_gpt(ocr_result)

            # Step 3: Validation
            logger.info("Validating fields...")
            validated_data, warnings = self.validator.validate_fields(
                extracted_data, ocr_result)

            # Prepare result
            result = {
                'status': 'success',
                'data': validated_data,
                'validation': {
                    'warnings': warnings,
                    'has_warnings': len(warnings) > 0,
                    'completeness_score': self.validator.completeness_score,
                    'accuracy_score': self.validator.accuracy_score,
                    'empty_fields': self.validator.empty_fields
                },
                'metadata': {
                    'file_path': file_path
                }
            }

            logger.info("Processing complete")
            return result

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'data': self._get_empty_result()
            }

    def _extract_with_gpt(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use GPT-4o to extract and normalize fields from OCR data
        """
        # Collect all OCR text with improved structure hints
        ocr_text = self._prepare_ocr_text_for_gpt(ocr_result)

        # System prompt focusing on accurate field extraction
        system_prompt = """You are an expert at extracting information from Israeli National Insurance (ביטוח לאומי) forms.

You will receive OCR text from form 283 (בקשה למתן טיפול רפואי לנפגע עבודה - עצמאי).
Extract ONLY the actual user-filled information, not the form's printed labels or instructions.

CRITICAL EXTRACTION RULES:
1. FIELD IDENTIFICATION: Look for handwritten/filled content next to field labels, not the labels themselves
2. EMPTY FIELDS: If no content is filled in a field, return "" - do not guess or use nearby text
3. SIGNATURE FIELD: Only extract if there's actual handwritten signature, NOT printed names from other parts of form  
4. DATES: Always format as DD/MM/YYYY with zero-padding (e.g., "02" not "2")
5. ID NUMBERS: Always read from LEFT TO RIGHT (Hebrew/Western reading direction), preserve 9 or 10 digit format
6. PHONE NUMBERS: Israeli mobile phones start with "05" - if you see "85" at start, it's OCR corruption, correct to "05"
7. OCR ARTIFACT CLEANING: Common corruptions include "0" becoming "8" in phone fields, clean these appropriately
8. CHECKBOXES: Only mark items that are explicitly checked/selected
9. MEDICAL SECTION: This is at the bottom - don't mix with main form fields

Form structure:
- פרטי התובע (Personal details) - top section
- פרטי התאונה (Injury details) - middle section  
- למילוי ע"י המוסד הרפואי (Medical institution) - bottom section

PHONE NUMBER VALIDATION:
- Mobile phones: Must start with "05" (if starts with "85", correct to "05")
- Landline phones: Usually start with "0" followed by area code
- If phone number seems corrupted by OCR artifacts, apply conservative cleaning

Be extremely careful to distinguish between different sections and only extract actual filled values."""

        user_prompt = f"""Extract user-filled information from this Israeli National Insurance form OCR:

{ocr_text}

IMPORTANT: Extract ONLY the values that users actually filled in, not form labels or instructions.
Pay special attention to distinguish between different date fields and sections.

Return ONLY a JSON object with this exact structure:
{{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  "gender": "",
  "dateOfBirth": {{"day": "", "month": "", "year": ""}},
  "address": {{
    "street": "", "houseNumber": "", "entrance": "", "apartment": "",
    "city": "", "postalCode": "", "poBox": ""
  }},
  "landlinePhone": "",
  "mobilePhone": "",
  "jobType": "",
  "dateOfInjury": {{"day": "", "month": "", "year": ""}},
  "timeOfInjury": "",
  "accidentLocation": "",
  "accidentAddress": "",
  "accidentDescription": "",
  "injuredBodyPart": "",
  "signature": "",
  "formFillingDate": {{"day": "", "month": "", "year": ""}},
  "formReceiptDateAtClinic": {{"day": "", "month": "", "year": ""}},
  "medicalInstitutionFields": {{
    "healthFundMember": "",
    "natureOfAccident": "",
    "medicalDiagnoses": ""
  }}
}}"""

        try:
            response = self.gpt_client.chat.completions.create(
                model=self.gpt_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=2000
            )

            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()

            # Try to parse JSON
            try:
                # Remove any markdown code blocks if present
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]

                extracted_data = json.loads(response_text)

                # Ensure all required fields exist
                return self._ensure_schema_compliance(extracted_data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT response as JSON: {e}")
                logger.error(f"Response was: {response_text[:500]}")
                return self._get_empty_result()

        except Exception as e:
            logger.error(f"GPT extraction failed: {e}")
            return self._get_empty_result()

    def _prepare_ocr_text_for_gpt(self, ocr_result: Dict[str, Any]) -> str:
        """
        Prepare OCR text for GPT processing with improved structure and artifact cleaning
        """
        text_parts = []

        # Process by pages to maintain structure
        for page in ocr_result.get('pages', []):
            page_num = page.get('page_number', 1)
            text_parts.append(f"\n=== PAGE {page_num} ===")

            # Group lines by approximate vertical position for better context
            lines = page.get('lines', [])
            if lines:
                # Sort lines by vertical position (top to bottom)
                sorted_lines = sorted(lines, key=lambda x: self._get_line_y_pos(x))

                for line in sorted_lines:
                    content = line.get('content', '').strip()
                    if content:
                        # Apply OCR artifact cleaning
                        cleaned_content = self._clean_ocr_artifacts(content)
                        text_parts.append(cleaned_content)

        # Add selection marks (checkboxes) with context
        checkbox_info = []
        for page in ocr_result.get('pages', []):
            for mark in page.get('selection_marks', []):
                state = mark.get('state', 'unselected')
                if state == 'selected':
                    checkbox_info.append(f"CHECKED checkbox found")

        if checkbox_info:
            text_parts.append("\n=== CHECKBOXES ===")
            text_parts.extend(checkbox_info)

        # Add key-value pairs if detected
        if ocr_result.get('key_value_pairs'):
            text_parts.append("\n=== KEY-VALUE PAIRS ===")
            for kv in ocr_result['key_value_pairs']:
                if kv.get('key') and kv.get('value'):
                    key_clean = self._clean_ocr_artifacts(kv['key'])
                    value_clean = self._clean_ocr_artifacts(kv['value'])
                    text_parts.append(f"{key_clean} → {value_clean}")

        # Add table content
        if ocr_result.get('tables'):
            text_parts.append("\n=== TABLE CONTENT ===")
            for table in ocr_result['tables']:
                for cell in table.get('cells', []):
                    if cell.get('content'):
                        cleaned_cell = self._clean_ocr_artifacts(cell['content'])
                        text_parts.append(cleaned_cell)

        # Add all available content as fallback
        all_content = ocr_result.get('content', [])
        if all_content:
            text_parts.append("\n=== ALL OCR CONTENT ===")
            for content in all_content:
                if isinstance(content, str) and content.strip():
                    cleaned_content = self._clean_ocr_artifacts(content.strip())
                    text_parts.append(cleaned_content)

        return "\n".join(text_parts)

    def _clean_ocr_artifacts(self, text: str) -> str:
        """
        Clean common OCR artifacts while preserving actual data
        """
        if not text:
            return text

        # Common OCR corrections for this specific form
        cleaned = text

        # Phone number specific corrections - Israeli mobile numbers
        import re

        # Mobile phone pattern: 85XXXXXXXX -> 05XXXXXXXX
        phone_pattern = r'\b85(\d{8})\b'
        cleaned = re.sub(phone_pattern, r'05\1', cleaned)

        # Also handle cases where the 8 might be standalone: "8 50XXXXXXX" -> "050XXXXXXX"
        spaced_phone_pattern = r'\b8\s*5(\d{8})\b'
        cleaned = re.sub(spaced_phone_pattern, r'05\1', cleaned)

        # Clean up extra spaces that might interfere
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    def _get_line_y_pos(self, line: Dict[str, Any]) -> float:
        """Get approximate Y position of a line for sorting"""
        polygon = line.get('polygon', [])
        if polygon:
            y_coords = [point.get('y', 0) for point in polygon if 'y' in point]
            return sum(y_coords) / len(y_coords) if y_coords else 0
        return 0

    def _ensure_schema_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure extracted data matches expected schema"""
        template = self._get_empty_result()

        def merge_with_template(extracted, template):
            if isinstance(template, dict):
                result = {}
                for key, value in template.items():
                    if key in extracted:
                        if isinstance(value, dict):
                            result[key] = merge_with_template(
                                extracted.get(key, {}), value)
                        else:
                            # Convert to string and handle None
                            extracted_value = extracted.get(key)
                            result[key] = str(
                                extracted_value) if extracted_value not in [
                                None, "null"] else ""
                    else:
                        result[key] = value
                return result
            return extracted if extracted is not None else template

        return merge_with_template(data, template)

    def _get_empty_result(self) -> Dict[str, Any]:
        """Get empty result template"""
        return {
            "lastName": "",
            "firstName": "",
            "idNumber": "",
            "gender": "",
            "dateOfBirth": {"day": "", "month": "", "year": ""},
            "address": {
                "street": "", "houseNumber": "", "entrance": "",
                "apartment": "",
                "city": "", "postalCode": "", "poBox": ""
            },
            "landlinePhone": "",
            "mobilePhone": "",
            "jobType": "",
            "dateOfInjury": {"day": "", "month": "", "year": ""},
            "timeOfInjury": "",
            "accidentLocation": "",
            "accidentAddress": "",
            "accidentDescription": "",
            "injuredBodyPart": "",
            "signature": "",
            "formFillingDate": {"day": "", "month": "", "year": ""},
            "formReceiptDateAtClinic": {"day": "", "month": "", "year": ""},
            "medicalInstitutionFields": {
                "healthFundMember": "",
                "natureOfAccident": "",
                "medicalDiagnoses": ""
            }
        }

    def process_batch(self, file_paths: list) -> list:
        """Process multiple forms"""
        results = []
        for file_path in file_paths:
            result = self.process_form(file_path)
            results.append(result)
        return results

    def save_result(self, result: Dict[str, Any], output_path: str):
        """Save processing result to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Result saved to {output_path}")


def main():
    """Main entry point for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Process Israeli National Insurance forms')
    parser.add_argument('input_file', help='Path to PDF/image file')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Process form
    processor = FormProcessor()
    result = processor.process_form(args.input_file)

    # Output result
    if args.output:
        processor.save_result(result, args.output)
    else:
        # Print extracted data
        print("=== EXTRACTED DATA ===")
        print(json.dumps(result['data'], ensure_ascii=False, indent=2))

        # Print validation summary
        validation = result.get('validation', {})
        print(f"\n=== VALIDATION SUMMARY ===")
        print(f"Completeness: {validation.get('completeness_score', 0):.1f}%")
        print(f"OCR Confidence: {validation.get('accuracy_score', 0):.1f}%")

        # Print warnings if any
        warnings = validation.get('warnings', [])
        if warnings:
            print(f"\n=== VALIDATION WARNINGS ({len(warnings)} total) ===")
            for warning in warnings:
                print(f"  • {warning}")


if __name__ == '__main__':
    main()