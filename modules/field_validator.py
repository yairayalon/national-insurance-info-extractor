from typing import Dict, Any, List, Tuple


class FieldValidator:
    def __init__(self):
        self.warnings = []
        self.completeness_score = 0.0
        self.accuracy_score = 0.0
        self.empty_fields = []

    def validate_fields(self, data: Dict[str, Any],
                        ocr_result: Dict[str, Any] = None) -> Tuple[
        Dict[str, Any], List[str]]:
        """
        Validate completeness and accuracy of extracted data

        Args:
            data: Field data to validate
            ocr_result: OCR result for confidence analysis

        Returns:
            Tuple of (data, warnings)
        """
        self.warnings = []
        self.empty_fields = []

        # Calculate completeness (which fields are empty)
        self.completeness_score = self._calculate_completeness(data)

        # Calculate accuracy (OCR confidence)
        self.accuracy_score = self._calculate_ocr_confidence(
            ocr_result) if ocr_result else 0.5

        # Basic format validation
        self._validate_formats(data)

        return data, self.warnings

    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score and identify empty fields"""
        total_fields = 0
        filled_fields = 0

        # All fields from schema to check
        fields_to_check = [
            'lastName', 'firstName', 'idNumber', 'gender',
            'dateOfBirth.day', 'dateOfBirth.month', 'dateOfBirth.year',
            'address.street', 'address.houseNumber', 'address.entrance',
            'address.apartment', 'address.city', 'address.postalCode',
            'address.poBox',
            'landlinePhone', 'mobilePhone', 'jobType',
            'dateOfInjury.day', 'dateOfInjury.month', 'dateOfInjury.year',
            'timeOfInjury', 'accidentLocation', 'accidentAddress',
            'accidentDescription', 'injuredBodyPart', 'signature',
            'formFillingDate.day', 'formFillingDate.month',
            'formFillingDate.year',
            'formReceiptDateAtClinic.day', 'formReceiptDateAtClinic.month',
            'formReceiptDateAtClinic.year',
            'medicalInstitutionFields.healthFundMember',
            'medicalInstitutionFields.natureOfAccident',
            'medicalInstitutionFields.medicalDiagnoses'
        ]

        for field_path in fields_to_check:
            total_fields += 1
            if self._is_field_filled(data, field_path):
                filled_fields += 1
            else:
                self.empty_fields.append(field_path)

        return (
                    filled_fields / total_fields * 100) if total_fields > 0 else 0.0

    def _calculate_ocr_confidence(self, ocr_result: Dict[str, Any]) -> float:
        """Calculate average OCR confidence score"""
        if not ocr_result or not ocr_result.get('words'):
            return 50.0  # Default when no confidence data available

        total_confidence = 0.0
        word_count = 0

        for word in ocr_result.get('words', []):
            if word.get('confidence') is not None:
                total_confidence += word['confidence']
                word_count += 1

        if word_count == 0:
            return 50.0

        return (total_confidence / word_count) * 100

    def _is_field_filled(self, data: Dict[str, Any], field_path: str) -> bool:
        """Check if a field (including nested) has a value"""
        parts = field_path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        return bool(str(current).strip()) if current is not None else False

    def _validate_formats(self, data: Dict[str, Any]):
        """Basic format validation"""
        # ID number
        if data.get('idNumber'):
            digits = ''.join(filter(str.isdigit, data['idNumber']))
            if len(digits) not in [9, 10]:
                self.warnings.append(
                    f"Invalid ID number length: {len(digits)} digits")

        # Mobile phone
        if data.get('mobilePhone'):
            digits = ''.join(filter(str.isdigit, data['mobilePhone']))
            if not digits.startswith('05') or len(digits) != 10:
                self.warnings.append("Invalid mobile phone format")

    def _is_date_complete(self, date_dict: Dict[str, str]) -> bool:
        """Check if date has all components"""
        return bool(
            date_dict.get('day') and date_dict.get('month') and date_dict.get(
                'year'))

    def _date_to_int(self, date_dict: Dict[str, str]) -> int:
        """Convert date to integer for comparison (YYYYMMDD)"""
        try:
            return int(date_dict['year']) * 10000 + int(
                date_dict['month']) * 100 + int(date_dict['day'])
        except (ValueError, KeyError):
            return 0