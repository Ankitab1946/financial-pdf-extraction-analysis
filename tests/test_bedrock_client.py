import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from bedrock_client import BedrockClient
from botocore.exceptions import ClientError

class TestBedrockClient:
    
    @pytest.fixture
    def bedrock_client(self):
        """Create a BedrockClient instance for testing"""
        with patch('boto3.client'):
            client = BedrockClient()
            client.bedrock_client = Mock()
            return client
    
    @pytest.fixture
    def sample_attributes_config(self):
        """Sample attributes configuration"""
        return [
            {
                'name': 'Total Revenue',
                'description': 'The total revenue reported in the financial statement',
                'data_type': 'currency',
                'required': True
            },
            {
                'name': 'Net Income',
                'description': 'The net income after all expenses',
                'data_type': 'currency',
                'required': True
            },
            {
                'name': 'Report Year',
                'description': 'The year of the financial report',
                'data_type': 'number',
                'required': True
            }
        ]
    
    @pytest.fixture
    def sample_financial_text(self):
        """Sample financial statement text"""
        return """
        FINANCIAL STATEMENT - Q1 2023
        
        Revenue: $1,500,000
        Cost of Goods Sold: $900,000
        Gross Profit: $600,000
        Operating Expenses: $400,000
        Net Income: $200,000
        
        Total Assets: $5,000,000
        Total Liabilities: $3,000,000
        Shareholders' Equity: $2,000,000
        """
    
    def test_extract_attributes_success(self, bedrock_client, sample_attributes_config, sample_financial_text):
        """Test successful attribute extraction"""
        # Mock successful Bedrock response
        mock_response_content = {
            "extraction_metadata": {
                "processing_date": "2024-01-15",
                "confidence_score": 0.95,
                "extraction_method": "bedrock_claude"
            },
            "extracted_attributes": {
                "Total Revenue": {
                    "value": "1500000",
                    "confidence": 0.95,
                    "source_text": "Revenue: $1,500,000"
                },
                "Net Income": {
                    "value": "200000",
                    "confidence": 0.90,
                    "source_text": "Net Income: $200,000"
                },
                "Report Year": {
                    "value": "2023",
                    "confidence": 0.98,
                    "source_text": "Q1 2023"
                }
            }
        }
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(mock_response_content)}]
        }).encode('utf-8')
        
        bedrock_client.bedrock_client.invoke_model.return_value = mock_response
        
        result = bedrock_client.extract_attributes(sample_financial_text, sample_attributes_config)
        
        assert 'extraction_metadata' in result
        assert 'extracted_attributes' in result
        assert result['extraction_metadata']['confidence_score'] == 0.95
        assert 'Total Revenue' in result['extracted_attributes']
        assert result['extracted_attributes']['Total Revenue']['value'] == "1500000"
        
        # Verify Bedrock client was called
        bedrock_client.bedrock_client.invoke_model.assert_called_once()
        call_args = bedrock_client.bedrock_client.invoke_model.call_args
        assert call_args[1]['modelId'] == bedrock_client.model_id
        assert call_args[1]['contentType'] == 'application/json'
    
    def test_extract_attributes_json_parsing_failure(self, bedrock_client, sample_attributes_config, sample_financial_text):
        """Test handling of JSON parsing failure in response"""
        # Mock response with invalid JSON
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Invalid JSON response from model'}]
        }).encode('utf-8')
        
        bedrock_client.bedrock_client.invoke_model.return_value = mock_response
        
        with patch.object(bedrock_client, '_extract_json_from_text') as mock_extract:
            mock_extract.return_value = {"error": "Failed to parse JSON"}
            
            result = bedrock_client.extract_attributes(sample_financial_text, sample_attributes_config)
            
            assert "error" in result
            mock_extract.assert_called_once()
    
    def test_extract_attributes_client_error(self, bedrock_client, sample_attributes_config, sample_financial_text):
        """Test handling of Bedrock client error"""
        bedrock_client.bedrock_client.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}},
            'InvokeModel'
        )
        
        result = bedrock_client.extract_attributes(sample_financial_text, sample_attributes_config)
        
        # Should return empty attributes response
        assert 'extraction_metadata' in result
        assert 'extracted_attributes' in result
        assert result['extraction_metadata']['confidence_score'] == 0.0
        assert 'error' in result['extraction_metadata']
    
    def test_chatbot_response_success(self, bedrock_client):
        """Test successful chatbot response generation"""
        user_input = "What is the total revenue?"
        context_data = {
            'consolidated_data': [
                {
                    'extracted_attributes': {
                        'Total Revenue': {'value': '1500000', 'confidence': 0.95}
                    }
                }
            ]
        }
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'The total revenue is $1,500,000 based on the extracted financial data.'}]
        }).encode('utf-8')
        
        bedrock_client.bedrock_client.invoke_model.return_value = mock_response
        
        result = bedrock_client.chatbot_response(user_input, context_data)
        
        assert isinstance(result, str)
        assert 'total revenue' in result.lower()
        assert '$1,500,000' in result
        
        # Verify the call was made with correct parameters
        bedrock_client.bedrock_client.invoke_model.assert_called_once()
        call_args = bedrock_client.bedrock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        assert request_body['temperature'] == 0.3
        assert request_body['max_tokens'] == 1000
    
    def test_chatbot_response_error(self, bedrock_client):
        """Test chatbot response with error"""
        user_input = "What is the revenue?"
        context_data = {}
        
        bedrock_client.bedrock_client.invoke_model.side_effect = Exception("API Error")
        
        result = bedrock_client.chatbot_response(user_input, context_data)
        
        assert "trouble processing your request" in result
    
    def test_build_extraction_system_prompt(self, bedrock_client, sample_attributes_config):
        """Test system prompt building for extraction"""
        prompt = bedrock_client._build_extraction_system_prompt(sample_attributes_config)
        
        assert "Total Revenue" in prompt
        assert "Net Income" in prompt
        assert "Report Year" in prompt
        assert "JSON format" in prompt
        assert "confidence" in prompt.lower()
    
    def test_prepare_context_summary(self, bedrock_client):
        """Test context summary preparation"""
        context_data = {
            'consolidated_data': [
                {
                    'extracted_attributes': {
                        'Total Revenue': {'value': '1000000'},
                        'Net Income': {'value': '150000'}
                    }
                },
                {
                    'extracted_attributes': {
                        'Total Revenue': {'value': '1200000'},
                        'Net Income': {'value': '180000'}
                    }
                }
            ]
        }
        
        summary = bedrock_client._prepare_context_summary(context_data)
        
        assert "2 PDF documents" in summary
        assert "Total Revenue" in summary
        assert "Net Income" in summary
    
    def test_prepare_context_summary_empty(self, bedrock_client):
        """Test context summary with empty data"""
        summary = bedrock_client._prepare_context_summary({})
        
        assert "No financial data available" in summary
    
    def test_extract_json_from_text_success(self, bedrock_client):
        """Test JSON extraction from text response"""
        text_with_json = '''
        Here is the extracted data:
        {
            "Total Revenue": {"value": "1000000", "confidence": 0.95},
            "Net Income": {"value": "150000", "confidence": 0.90}
        }
        Additional text after JSON.
        '''
        
        result = bedrock_client._extract_json_from_text(text_with_json)
        
        assert isinstance(result, dict)
        assert "Total Revenue" in result
        assert result["Total Revenue"]["value"] == "1000000"
    
    def test_extract_json_from_text_no_json(self, bedrock_client):
        """Test JSON extraction when no JSON is found"""
        text_without_json = "This text contains no JSON data."
        
        result = bedrock_client._extract_json_from_text(text_without_json)
        
        assert "error" in result
        assert "Failed to parse JSON response" in result["error"]
    
    def test_get_empty_attributes_response(self, bedrock_client, sample_attributes_config):
        """Test empty attributes response generation"""
        result = bedrock_client._get_empty_attributes_response(sample_attributes_config)
        
        assert 'extraction_metadata' in result
        assert 'extracted_attributes' in result
        assert result['extraction_metadata']['confidence_score'] == 0.0
        assert 'error' in result['extraction_metadata']
        
        # Check all attributes are present with null values
        for attr in sample_attributes_config:
            attr_name = attr['name']
            assert attr_name in result['extracted_attributes']
            assert result['extracted_attributes'][attr_name]['value'] is None
            assert result['extracted_attributes'][attr_name]['confidence'] == 0.0
    
    @patch.dict('os.environ', {
        'AWS_REGION': 'us-west-2',
        'BEDROCK_MODEL_ID': 'anthropic.claude-3-haiku-20240307-v1:0'
    })
    def test_initialization_with_env_vars(self):
        """Test BedrockClient initialization with environment variables"""
        with patch('boto3.client') as mock_boto_client:
            client = BedrockClient()
            
            assert client.region_name == 'us-west-2'
            assert client.model_id == 'anthropic.claude-3-haiku-20240307-v1:0'
            
            mock_boto_client.assert_called_once_with(
                'bedrock-runtime',
                region_name='us-west-2',
                aws_access_key_id=None,
                aws_secret_access_key=None,
                aws_session_token=None
            )
    
    def test_initialization_failure(self):
        """Test BedrockClient initialization failure"""
        with patch('boto3.client') as mock_boto_client:
            mock_boto_client.side_effect = Exception("AWS credentials not found")
            
            with pytest.raises(Exception) as exc_info:
                BedrockClient()
            
            assert "AWS credentials not found" in str(exc_info.value)
    
    def test_long_text_truncation(self, bedrock_client, sample_attributes_config):
        """Test that long text is properly truncated"""
        # Create a very long text (more than 8000 characters)
        long_text = "Financial data: " + "A" * 10000
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"extracted_attributes": {}}'}]
        }).encode('utf-8')
        
        bedrock_client.bedrock_client.invoke_model.return_value = mock_response
        
        bedrock_client.extract_attributes(long_text, sample_attributes_config)
        
        # Verify the call was made and check the request body
        call_args = bedrock_client.bedrock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])
        user_message = request_body['messages'][0]['content'][0]['text']
        
        # The text should be truncated to 8000 characters plus some additional text
        assert len(user_message) < len(long_text) + 1000  # Some buffer for additional prompt text
