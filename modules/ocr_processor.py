from typing import Dict, Any, Optional, List
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.exceptions import AzureError
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self, endpoint: str, key: str):
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    def process_document(self, document_path: str) -> Dict[str, Any]:
        """
        Process document with OCR, optionally limiting to active pages

        Args:
            document_path: Path to PDF/image file

        Returns:
            OCR analysis result
        """
        try:
            with open(document_path, 'rb') as f:
                document_content = f.read()

            # Start with the most basic configuration
            result = None

            # Try different configurations in order of preference
            configurations = [
                # Config 1: With locale and features (best case)
                {
                    "model_id": "prebuilt-layout",
                    "body": document_content,
                    "content_type": "application/pdf",
                    "features": ["selectionMarks"],
                    "locale": "he"
                },
                # Config 2: With locale, no features
                {
                    "model_id": "prebuilt-layout",
                    "body": document_content,
                    "content_type": "application/pdf",
                    "locale": "he"
                },
                # Config 3: Basic layout only (fallback)
                {
                    "model_id": "prebuilt-layout",
                    "body": document_content,
                    "content_type": "application/pdf"
                },
                # Config 4: Try prebuilt-document model
                {
                    "model_id": "prebuilt-document",
                    "body": document_content,
                    "content_type": "application/pdf"
                }
            ]

            for i, config in enumerate(configurations):
                try:
                    logger.info(
                        f"Trying configuration {i + 1}: {config.get('model_id')} with features={config.get('features', 'none')}, locale={config.get('locale', 'none')}")
                    poller = self.client.begin_analyze_document(**config)
                    result = poller.result()
                    logger.info(
                        f"Successfully processed with configuration {i + 1}")
                    break
                except AzureError as e:
                    logger.warning(
                        f"Configuration {i + 1} failed: {str(e)[:100]}")
                    if i == len(configurations) - 1:
                        # Last configuration failed, raise the error
                        raise
                    continue

            if not result:
                raise Exception(
                    "Failed to process document with any configuration")

            return self._process_result(result)

        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            raise

    def _process_result(self, result: AnalyzeResult) -> Dict[str, Any]:
        """Process and structure OCR result"""
        processed = {
            'pages': [],
            'paragraphs': [],
            'tables': [],
            'selection_marks': [],
            'key_value_pairs': [],
            'lines': [],
            'words': [],
            'content': []  # Store all text content for fallback processing
        }

        # Extract pages
        if hasattr(result, 'pages') and result.pages:
            for page in result.pages:
                page_info = {
                    'page_number': getattr(page, 'page_number', 1),
                    'width': getattr(page, 'width', 0),
                    'height': getattr(page, 'height', 0),
                    'unit': getattr(page, 'unit', 'pixel'),
                    'words': [],
                    'lines': [],
                    'selection_marks': []
                }

                # Extract words
                if hasattr(page, 'words') and page.words:
                    for word in page.words:
                        word_info = {
                            'content': getattr(word, 'content', ''),
                            'polygon': self._safe_polygon(word),
                            'confidence': getattr(word, 'confidence', 0.0)
                        }
                        page_info['words'].append(word_info)
                        processed['words'].append(word_info)

                # Extract lines
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        line_info = {
                            'content': getattr(line, 'content', ''),
                            'polygon': self._safe_polygon(line),
                            'page_number': page_info['page_number']
                        }
                        page_info['lines'].append(line_info)
                        processed['lines'].append(line_info)
                        # Add to content for fallback processing
                        processed['content'].append(line_info['content'])

                # Extract selection marks if available
                if hasattr(page, 'selection_marks') and page.selection_marks:
                    for mark in page.selection_marks:
                        mark_info = {
                            'state': getattr(mark, 'state', 'unselected'),
                            'polygon': self._safe_polygon(mark),
                            'confidence': getattr(mark, 'confidence', 0.0),
                            'page_number': page_info['page_number']
                        }
                        page_info['selection_marks'].append(mark_info)
                        processed['selection_marks'].append(mark_info)

                processed['pages'].append(page_info)

        # Extract paragraphs
        if hasattr(result, 'paragraphs') and result.paragraphs:
            for para in result.paragraphs:
                para_info = {
                    'content': getattr(para, 'content', ''),
                    'bounding_regions': []
                }
                if hasattr(para, 'bounding_regions'):
                    for region in para.bounding_regions:
                        para_info['bounding_regions'].append({
                            'page_number': getattr(region, 'page_number', 1),
                            'polygon': self._safe_polygon(region)
                        })
                processed['paragraphs'].append(para_info)
                # Add to content
                if para_info['content']:
                    processed['content'].append(para_info['content'])

        # Extract tables
        if hasattr(result, 'tables') and result.tables:
            for table in result.tables:
                table_info = self._process_table(table)
                if table_info:
                    processed['tables'].append(table_info)

        # Extract key-value pairs
        if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
            for kv_pair in result.key_value_pairs:
                kv_info = self._process_key_value(kv_pair)
                if kv_info:
                    processed['key_value_pairs'].append(kv_info)

        # Extract content from result if available
        if hasattr(result, 'content') and result.content:
            processed['content'].append(result.content)

        # Log summary
        logger.info(f"OCR Result: {len(processed['pages'])} pages, "
                    f"{len(processed['lines'])} lines, {len(processed['words'])} words, "
                    f"{len(processed['selection_marks'])} checkboxes, "
                    f"{len(processed['key_value_pairs'])} key-value pairs")

        return processed

    def _safe_polygon(self, obj) -> List[Dict[str, float]]:
        """Safely extract polygon from object"""
        if hasattr(obj, 'polygon'):
            return self._normalize_polygon(obj.polygon)
        return []

    def _normalize_polygon(self, polygon) -> List[Dict[str, float]]:
        """Normalize polygon coordinates to consistent format"""
        if not polygon:
            return []

        try:
            points = []

            # Check if it's a flat list of numbers
            if isinstance(polygon, list) and len(polygon) > 0:
                if isinstance(polygon[0], (int, float)):
                    # Flat array [x1, y1, x2, y2, ...]
                    for i in range(0, len(polygon), 2):
                        if i + 1 < len(polygon):
                            points.append({
                                'x': float(polygon[i]),
                                'y': float(polygon[i + 1])
                            })
                else:
                    # List of point objects
                    for p in polygon:
                        if hasattr(p, 'x') and hasattr(p, 'y'):
                            points.append({'x': float(p.x), 'y': float(p.y)})
                        elif isinstance(p, dict) and 'x' in p and 'y' in p:
                            points.append(
                                {'x': float(p['x']), 'y': float(p['y'])})
                        elif isinstance(p, (list, tuple)) and len(p) >= 2:
                            points.append({'x': float(p[0]), 'y': float(p[1])})

            return points
        except Exception as e:
            logger.debug(f"Could not normalize polygon: {e}")
            return []

    def _process_table(self, table) -> Optional[Dict[str, Any]]:
        """Process table data"""
        try:
            table_info = {
                'row_count': getattr(table, 'row_count', 0),
                'column_count': getattr(table, 'column_count', 0),
                'cells': []
            }

            if hasattr(table, 'cells'):
                for cell in table.cells:
                    cell_info = {
                        'row_index': getattr(cell, 'row_index', 0),
                        'column_index': getattr(cell, 'column_index', 0),
                        'content': getattr(cell, 'content', ''),
                        'row_span': getattr(cell, 'row_span', 1),
                        'column_span': getattr(cell, 'column_span', 1)
                    }
                    table_info['cells'].append(cell_info)

            return table_info
        except Exception as e:
            logger.debug(f"Error processing table: {e}")
            return None

    def _process_key_value(self, kv_pair) -> Optional[Dict[str, Any]]:
        """Process key-value pair"""
        try:
            kv_info = {
                'key': '',
                'value': '',
                'confidence': 0.0
            }

            if hasattr(kv_pair, 'key') and kv_pair.key:
                kv_info['key'] = getattr(kv_pair.key, 'content', '')

            if hasattr(kv_pair, 'value') and kv_pair.value:
                kv_info['value'] = getattr(kv_pair.value, 'content', '')

            if hasattr(kv_pair, 'confidence'):
                kv_info['confidence'] = float(kv_pair.confidence)

            return kv_info if (kv_info['key'] or kv_info['value']) else None
        except Exception as e:
            logger.debug(f"Error processing key-value: {e}")
            return None