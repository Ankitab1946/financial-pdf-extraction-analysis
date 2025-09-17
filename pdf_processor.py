import boto3
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io
import logging
from typing import List, Dict, Any, Optional, Tuple
import os
from botocore.exceptions import ClientError
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handle PDF processing including S3 operations, text extraction, and OCR"""
    
    def __init__(self, region_name: str = None):
        from env_config import get_s3_config, get_aws_session
        
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.s3_config = get_s3_config()
        
        try:
            session = get_aws_session()
            self.s3_client = session.client('s3')
            logger.info(f"S3 client initialized for region: {self.region_name}")
            logger.info(f"S3 config: {self.s3_config}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def list_pdfs_from_s3(self, bucket_name: str = None) -> List[Dict[str, Any]]:
        """
        List all PDF files in the S3 input location
        
        Args:
            bucket_name: Name of the S3 bucket (optional, uses config if not provided)
            
        Returns:
            List of dictionaries containing PDF file information
        """
        try:
            # Determine bucket and prefix based on configuration
            if self.s3_config['use_single_bucket']:
                bucket = self.s3_config['bucket_name']
                prefix = f"{self.s3_config['input_folder']}/"
            else:
                bucket = bucket_name or self.s3_config['input_bucket']
                prefix = ""
            
            if not bucket:
                raise Exception("No S3 bucket configured for input")
            
            logger.info(f"Listing PDFs from bucket: {bucket}, prefix: {prefix}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.info(f"No files found in bucket: {bucket} with prefix: {prefix}")
                return []
            
            pdf_files = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.lower().endswith('.pdf') and key != prefix:  # Exclude the folder itself
                    # Extract filename from key (remove prefix)
                    filename = key.replace(prefix, '') if prefix else os.path.basename(key)
                    
                    pdf_info = {
                        'key': key,
                        'filename': filename,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'size_mb': round(obj['Size'] / (1024 * 1024), 2),
                        'bucket': bucket
                    }
                    pdf_files.append(pdf_info)
            
            logger.info(f"Found {len(pdf_files)} PDF files in {bucket}/{prefix}")
            return sorted(pdf_files, key=lambda x: x['last_modified'], reverse=True)
            
        except ClientError as e:
            logger.error(f"Error listing PDFs from S3: {str(e)}")
            raise Exception(f"Failed to access S3 bucket: {bucket}")
        except Exception as e:
            logger.error(f"Unexpected error listing PDFs: {str(e)}")
            raise
    
    def download_pdf(self, bucket_name: str, key: str) -> bytes:
        """
        Download PDF file from S3
        
        Args:
            bucket_name: Name of the S3 bucket
            key: S3 object key
            
        Returns:
            PDF file content as bytes
        """
        try:
            # Check file size first
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)
            file_size = response['ContentLength']
            
            if file_size > self.max_file_size:
                raise Exception(f"File too large: {file_size / (1024*1024):.2f}MB (max: {self.max_file_size / (1024*1024)}MB)")
            
            # Download the file
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            pdf_content = response['Body'].read()
            
            logger.info(f"Downloaded PDF: {key} ({file_size / (1024*1024):.2f}MB)")
            return pdf_content
            
        except ClientError as e:
            logger.error(f"Error downloading PDF from S3: {str(e)}")
            raise Exception(f"Failed to download PDF: {key}")
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_bytes: bytes, filename: str = "unknown.pdf") -> Dict[str, Any]:
        """
        Extract text from PDF using multiple methods
        
        Args:
            pdf_bytes: PDF file content as bytes
            filename: Original filename for logging
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        start_time = time.time()
        result = {
            'filename': filename,
            'text': '',
            'page_count': 0,
            'extraction_method': '',
            'processing_time': 0,
            'has_text': False,
            'has_images': False,
            'confidence_score': 0.0,
            'errors': []
        }
        
        try:
            # First, try with pdfplumber (best for text-based PDFs)
            text_content = self._extract_with_pdfplumber(pdf_bytes)
            
            if text_content and len(text_content.strip()) > 100:
                result.update({
                    'text': text_content,
                    'extraction_method': 'pdfplumber',
                    'has_text': True,
                    'confidence_score': 0.95
                })
                logger.info(f"Successfully extracted text using pdfplumber: {filename}")
            else:
                # If pdfplumber fails, try PyMuPDF
                text_content = self._extract_with_pymupdf(pdf_bytes)
                
                if text_content and len(text_content.strip()) > 100:
                    result.update({
                        'text': text_content,
                        'extraction_method': 'pymupdf',
                        'has_text': True,
                        'confidence_score': 0.90
                    })
                    logger.info(f"Successfully extracted text using PyMuPDF: {filename}")
                else:
                    # If both fail, try OCR
                    ocr_result = self._extract_with_ocr(pdf_bytes)
                    result.update(ocr_result)
                    logger.info(f"Used OCR for text extraction: {filename}")
            
            # Get page count
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                result['page_count'] = len(doc)
                doc.close()
            except Exception as e:
                logger.warning(f"Could not get page count: {str(e)}")
            
            result['processing_time'] = round(time.time() - start_time, 2)
            
            if not result['text'] or len(result['text'].strip()) < 50:
                result['errors'].append("Insufficient text extracted from PDF")
                result['confidence_score'] = 0.1
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filename}: {str(e)}")
            result.update({
                'errors': [str(e)],
                'processing_time': round(time.time() - start_time, 2),
                'confidence_score': 0.0
            })
            return result
    
    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber"""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return '\n'.join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")
            return ""
    
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        """Extract text using PyMuPDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            doc.close()
            return '\n'.join(text_parts)
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {str(e)}")
            return ""
    
    def _extract_with_ocr(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract text using OCR for scanned PDFs"""
        ocr_result = {
            'text': '',
            'extraction_method': 'ocr',
            'has_text': False,
            'has_images': True,
            'confidence_score': 0.0,
            'errors': []
        }
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            total_confidence = 0
            page_count = 0
            
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages for performance
                page = doc.load_page(page_num)
                
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # Increase resolution
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Perform OCR
                image = Image.open(io.BytesIO(img_data))
                
                # Get OCR data with confidence scores
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Extract text and calculate confidence
                page_text_parts = []
                confidences = []
                
                for i, word in enumerate(ocr_data['text']):
                    if word.strip():
                        confidence = int(ocr_data['conf'][i])
                        if confidence > 30:  # Only include words with reasonable confidence
                            page_text_parts.append(word)
                            confidences.append(confidence)
                
                if page_text_parts:
                    page_text = ' '.join(page_text_parts)
                    text_parts.append(page_text)
                    
                    if confidences:
                        page_confidence = sum(confidences) / len(confidences)
                        total_confidence += page_confidence
                        page_count += 1
            
            doc.close()
            
            if text_parts:
                ocr_result.update({
                    'text': '\n'.join(text_parts),
                    'has_text': True,
                    'confidence_score': (total_confidence / page_count / 100) if page_count > 0 else 0.0
                })
            else:
                ocr_result['errors'].append("OCR could not extract readable text")
            
            return ocr_result
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            ocr_result['errors'].append(f"OCR failed: {str(e)}")
            return ocr_result
    
    def process_multiple_pdfs(self, bucket_name: str, pdf_keys: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple PDFs concurrently
        
        Args:
            bucket_name: S3 bucket name
            pdf_keys: List of S3 object keys
            
        Returns:
            List of processing results
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all download and processing tasks
            future_to_key = {}
            
            for key in pdf_keys:
                future = executor.submit(self._process_single_pdf, bucket_name, key)
                future_to_key[future] = key
            
            # Collect results as they complete
            for future in future_to_key:
                key = future_to_key[future]
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per PDF
                    results.append(result)
                    logger.info(f"Completed processing: {key}")
                except Exception as e:
                    logger.error(f"Failed to process {key}: {str(e)}")
                    results.append({
                        'filename': os.path.basename(key),
                        'key': key,
                        'text': '',
                        'error': str(e),
                        'processing_time': 0,
                        'confidence_score': 0.0
                    })
        
        return results
    
    def _process_single_pdf(self, bucket_name: str, key: str) -> Dict[str, Any]:
        """Process a single PDF file"""
        try:
            # Download PDF
            pdf_bytes = self.download_pdf(bucket_name, key)
            
            # Extract text
            extraction_result = self.extract_text_from_pdf(pdf_bytes, os.path.basename(key))
            extraction_result['key'] = key
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Error processing PDF {key}: {str(e)}")
            return {
                'filename': os.path.basename(key),
                'key': key,
                'text': '',
                'error': str(e),
                'processing_time': 0,
                'confidence_score': 0.0
            }
    
    def validate_pdf(self, pdf_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate if the file is a proper PDF
        
        Args:
            pdf_bytes: PDF file content
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()
            
            if page_count == 0:
                return False, "PDF has no pages"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
