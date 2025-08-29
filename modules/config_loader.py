import os
import json
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    def __init__(self):
        load_dotenv()
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load all configuration from environment and files"""
        config = {
            # Azure Document Intelligence
            'doc_intelligence': {
                'endpoint': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'),
                'key': os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
            },
            # Azure OpenAI
            'openai': {
                'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
                'key': os.getenv('AZURE_OPENAI_KEY'),
                'model': os.getenv('AZURE_OPENAI_MODEL', 'gpt-4o'),
                'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
            }
        }

        # Load schemas (kept for potential future use)
        schema_english_path = 'config/schema_english.json'
        if os.path.exists(schema_english_path):
            with open(schema_english_path, 'r', encoding='utf-8') as f:
                config['schema_english'] = json.load(f)
        else:
            config['schema_english'] = self._get_default_english_schema()

        schema_hebrew_path = 'config/schema_hebrew.json'
        if os.path.exists(schema_hebrew_path):
            with open(schema_hebrew_path, 'r', encoding='utf-8') as f:
                config['schema_hebrew'] = json.load(f)
        else:
            config['schema_hebrew'] = self._get_default_hebrew_schema()

        return config

    def get(self, key: str, default=None):
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def _get_default_english_schema(self) -> Dict:
        """Return default English schema"""
        return {
            "lastName": "string",
            "firstName": "string",
            "idNumber": "string",
            "gender": "string",
            "dateOfBirth": {"day": "string", "month": "string", "year": "string"},
            "address": {
                "street": "string", "houseNumber": "string", "entrance": "string",
                "apartment": "string", "city": "string", "postalCode": "string", "poBox": "string"
            },
            "landlinePhone": "string",
            "mobilePhone": "string",
            "jobType": "string",
            "dateOfInjury": {"day": "string", "month": "string", "year": "string"},
            "timeOfInjury": "string",
            "accidentLocation": "string",
            "accidentAddress": "string",
            "accidentDescription": "string",
            "injuredBodyPart": "string",
            "signature": "string",
            "formFillingDate": {"day": "string", "month": "string", "year": "string"},
            "formReceiptDateAtClinic": {"day": "string", "month": "string", "year": "string"},
            "medicalInstitutionFields": {
                "healthFundMember": "string",
                "natureOfAccident": "string",
                "medicalDiagnoses": "string"
            }
        }

    def _get_default_hebrew_schema(self) -> Dict:
        """Return default Hebrew schema"""
        return {
            "שם משפחה": "string",
            "שם פרטי": "string",
            "מספר זהות": "string",
            "מין": "string",
            "תאריך לידה": {"יום": "string", "חודש": "string", "שנה": "string"},
            "כתובת": {
                "רחוב": "string", "מספר בית": "string", "כניסה": "string",
                "דירה": "string", "ישוב": "string", "מיקוד": "string", "תא דואר": "string"
            },
            "טלפון קווי": "string",
            "טלפון נייד": "string",
            "סוג העבודה": "string",
            "תאריך הפגיעה": {"יום": "string", "חודש": "string", "שנה": "string"},
            "שעת הפגיעה": "string",
            "מקום התאונה": "string",
            "כתובת מקום התאונה": "string",
            "תיאור התאונה": "string",
            "האיבר שנפגע": "string",
            "חתימה": "string",
            "תאריך מילוי הטופס": {"יום": "string", "חודש": "string", "שנה": "string"},
            "תאריך קבלת הטופס בקופה": {"יום": "string", "חודש": "string", "שנה": "string"},
            "למילוי ע\"י המוסד הרפואי": {
                "חבר בקופת חולים": "string",
                "מהות התאונה": "string",
                "אבחנות רפואיות": "string"
            }
        }