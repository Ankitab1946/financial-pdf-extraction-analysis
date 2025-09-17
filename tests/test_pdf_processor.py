import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from pdf_processor import PDFProcessor
import boto3
from botocore.exceptions import ClientError

class TestPDFProcessor:
    
    @pytest.fixture
    def pdf_processor(self):
        """Create a PDFProcessor instance for testing"""
        with patch('boto3.client'):
            processor = PDFProcessor()
            processor.s3_client = Mock()
            return processor
    
    @pytest.fixture
    def sample_pdf_list(self):
        """Sample PDF list response from S3"""
        return [
            {
                'key': 'financial_statements/Q1_2023.pdf',
                'filename': 'Q1_2023.pdf',
                'size': 1024000,
                'last_modified': '2023-01-15T10:30:00Z',
                'size_mb': 1.0
            },
            {
                'key': 'financial_statements/Q2_2023.pdf',
                'filename': 'Q2_2023.pdf',
                'size': 2048000,
                'last_modified': '2023-04-15T10:30:00Z',
                'size_mb': 2.0
            }
        ]
    
    def test_list_pdfs_from_s3_success(self, pdf_processor, sample_pdf_list):
        """Test successful PDF listing from S3"""
        # Mock S3 response
        mock_response = {
            'Contents': [
                {
                    'Key': 'financial_statements/Q1_2023.pdf',
                    'Size': 1024000,
                    'LastModified': '2023-01-15T10:30:00Z'
                },
                {
                    'Key': 'financial_statements/Q2_2023.pdf',
                    'Size': 2048000,
                    'LastModified': '2023-04-15T10:30:00Z'
                },
                {
                    'Key': 'other_files/document.txt',  # Non-PDF file
                    'Size': 512000,
                    'LastModified': '2023-01-10T10:30:00Z'
                }
            ]
        }
        
        pdf_processor.s3_client.list_objects_v2.return_value = mock_response
        
        result = pdf_processor.list_pdfs_from_s3('test-bucket')
        
        # Should only return PDF files
        assert len(result) == 2
        assert all(pdf['filename'].endswith('.pdf') for pdf in result)
        # Results are sorted by last_modified in reverse order, so Q2 comes first
        assert result[0]['filename'] == 'Q2_2023.pdf'
        assert result[1]['filename'] == 'Q1_2023.pdf'
        
        # Verify S3 client was called correctly
        pdf_processor.s3_client.list_objects_v2.assert_called_once_with(Bucket='test-bucket')
    
    def test_list_pdfs_from_s3_empty_bucket(self, pdf_processor):
        """Test listing PDFs from empty bucket"""
        pdf_processor.s3_client.list_objects_v2.return_value = {}
        
        result = pdf_processor.list_pdfs_from_s3('empty-bucket')
        
        assert result == []
    
    def test_list_pdfs_from_s3_client_error(self, pdf_processor):
        """Test S3 client error handling"""
        pdf_processor.s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
            'ListObjectsV2'
        )
        
        with pytest.raises(Exception) as exc_info:
            pdf_processor.list_pdfs_from_s3('nonexistent-bucket')
        
        assert "Failed to access S3 bucket" in str(exc_info.value)
    
    def test_download_pdf_success(self, pdf_processor):
        """Test successful PDF download"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        
        # Mock head_object response
        pdf_processor.s3_client.head_object.return_value = {
            'ContentLength': len(mock_pdf_content)
        }
        
        # Mock get_object response
        mock_body = Mock()
        mock_body.read.return_value = mock_pdf_content
        pdf_processor.s3_client.get_object.return_value = {
            'Body': mock_body
        }
        
        result = pdf_processor.download_pdf('test-bucket', 'test.pdf')
        
        assert result == mock_pdf_content
        pdf_processor.s3_client.head_object.assert_called_once_with(
            Bucket='test-bucket', Key='test.pdf'
        )
        pdf_processor.s3_client.get_object.assert_called_once_with(
            Bucket='test-bucket', Key='test.pdf'
        )
    
    def test_download_pdf_file_too_large(self, pdf_processor):
        """Test download failure for oversized file"""
        large_file_size = 200 * 1024 * 1024  # 200MB
        
        pdf_processor.s3_client.head_object.return_value = {
            'ContentLength': large_file_size
        }
        
        with pytest.raises(Exception) as exc_info:
            pdf_processor.download_pdf('test-bucket', 'large.pdf')
        
        assert "File too large" in str(exc_info.value)
    
    def test_download_pdf_client_error(self, pdf_processor):
        """Test download with S3 client error"""
        pdf_processor.s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Key does not exist'}},
            'HeadObject'
        )
        
        with pytest.raises(Exception) as exc_info:
            pdf_processor.download_pdf('test-bucket', 'nonexistent.pdf')
        
        assert "Failed to download PDF" in str(exc_info.value)
    
    def test_extract_text_with_pdfplumber_success(self, pdf_processor):
        """Test successful text extraction with pdfplumber"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        mock_text = "Sample financial statement text with revenue data"
        
        # Mock the internal methods directly
        with patch.object(pdf_processor, '_extract_with_pdfplumber', return_value=mock_text):
            with patch('pdf_processor.fitz') as mock_fitz:
                mock_doc = Mock()
                mock_doc.__len__ = Mock(return_value=1)
                mock_fitz.open.return_value = mock_doc
                
                result = pdf_processor.extract_text_from_pdf(mock_pdf_content, 'test.pdf')
        
        assert result['text'] == mock_text
        assert result['extraction_method'] == 'pdfplumber'
        assert result['has_text'] is True
        assert result['confidence_score'] == 0.95
        assert result['filename'] == 'test.pdf'
    
    def test_extract_text_fallback_to_pymupdf(self, pdf_processor):
        """Test fallback to PyMuPDF when pdfplumber fails"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        mock_text = "Financial data extracted with PyMuPDF"
        
        # Mock pdfplumber failure and PyMuPDF success
        with patch.object(pdf_processor, '_extract_with_pdfplumber', return_value=""):
            with patch.object(pdf_processor, '_extract_with_pymupdf', return_value=mock_text):
                with patch('pdf_processor.fitz') as mock_fitz:
                    mock_doc = Mock()
                    mock_doc.__len__ = Mock(return_value=1)
                    mock_fitz.open.return_value = mock_doc
                    
                    result = pdf_processor.extract_text_from_pdf(mock_pdf_content, 'test.pdf')
        
        assert result['text'] == mock_text
        assert result['extraction_method'] == 'pymupdf'
        assert result['confidence_score'] == 0.90
    
    def test_extract_text_fallback_to_ocr(self, pdf_processor):
        """Test fallback to OCR when other methods fail"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        mock_ocr_result = {
            'text': 'OCR extracted financial data',
            'extraction_method': 'ocr',
            'has_text': True,
            'has_images': True,
            'confidence_score': 0.75,
            'errors': []
        }
        
        # Mock both pdfplumber and PyMuPDF failure, OCR success
        with patch.object(pdf_processor, '_extract_with_pdfplumber', return_value=""):
            with patch.object(pdf_processor, '_extract_with_pymupdf', return_value=""):
                with patch.object(pdf_processor, '_extract_with_ocr', return_value=mock_ocr_result):
                    with patch('pdf_processor.fitz') as mock_fitz:
                        mock_doc = Mock()
                        mock_doc.__len__ = Mock(return_value=1)
                        mock_fitz.open.return_value = mock_doc
                        
                        result = pdf_processor.extract_text_from_pdf(mock_pdf_content, 'test.pdf')
        
        assert result['extraction_method'] == 'ocr'
        assert result['has_images'] is True
        assert 'OCR extracted financial data' in result['text']
    
    def test_validate_pdf_success(self, pdf_processor):
        """Test successful PDF validation"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        
        with patch('pdf_processor.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=5)  # 5 pages
            mock_fitz.open.return_value = mock_doc
            
            is_valid, error_msg = pdf_processor.validate_pdf(mock_pdf_content)
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_pdf_no_pages(self, pdf_processor):
        """Test PDF validation with no pages"""
        mock_pdf_content = b'%PDF-1.4 fake pdf content'
        
        with patch('pdf_processor.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.__len__ = Mock(return_value=0)  # No pages
            mock_fitz.open.return_value = mock_doc
            
            is_valid, error_msg = pdf_processor.validate_pdf(mock_pdf_content)
        
        assert is_valid is False
        assert "PDF has no pages" in error_msg
    
    def test_validate_pdf_invalid_file(self, pdf_processor):
        """Test PDF validation with invalid file"""
        invalid_content = b'This is not a PDF file'
        
        with patch('pdf_processor.fitz') as mock_fitz:
            mock_fitz.open.side_effect = Exception("Invalid PDF format")
            
            is_valid, error_msg = pdf_processor.validate_pdf(invalid_content)
        
        assert is_valid is False
        assert "Invalid PDF file" in error_msg
    
    def test_process_multiple_pdfs(self, pdf_processor):
        """Test processing multiple PDFs concurrently"""
        pdf_keys = ['pdf1.pdf', 'pdf2.pdf']
        bucket_name = 'test-bucket'
        
        # Mock the _process_single_pdf method
        with patch.object(pdf_processor, '_process_single_pdf') as mock_process:
            mock_process.side_effect = [
                {'filename': 'pdf1.pdf', 'text': 'Content 1', 'confidence_score': 0.9},
                {'filename': 'pdf2.pdf', 'text': 'Content 2', 'confidence_score': 0.8}
            ]
            
            results = pdf_processor.process_multiple_pdfs(bucket_name, pdf_keys)
        
        assert len(results) == 2
        assert results[0]['filename'] == 'pdf1.pdf'
        assert results[1]['filename'] == 'pdf2.pdf'
        assert mock_process.call_count == 2
