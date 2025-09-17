import boto3
import json
import logging
from typing import Dict, List, Any
import os
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)

class BedrockClient:
    """AWS Bedrock client for Claude model interactions"""
    
    def __init__(self, region_name: str = None, model_id: str = None):
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.model_id = model_id or os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.getenv('AWS_SESSION_TOKEN')
            )
            logger.info(f"Bedrock client initialized for region: {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def extract_attributes(self, text: str, attributes_config: List[Dict]) -> Dict[str, Any]:
        """
        Extract financial attributes from PDF text using Claude
        
        Args:
            text: Extracted text from PDF
            attributes_config: List of attributes to extract from config
            
        Returns:
            Dictionary containing extracted attributes with confidence scores
        """
        try:
            # Prepare the system prompt for attribute extraction
            system_prompt = self._build_extraction_system_prompt(attributes_config)
            
            # Prepare the user message
            user_message = f"""
            Please analyze the following financial document text and extract the requested attributes.
            Return the results in JSON format with the exact attribute names as keys.
            If an attribute cannot be found, set its value to null and confidence to 0.
            
            Financial Document Text:
            {text[:8000]}  # Limit text to avoid token limits
            """
            
            # Prepare the request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            }
            
            # Make the API call
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json'
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            extracted_text = response_body['content'][0]['text']
            
            # Parse JSON from the response
            try:
                extracted_data = json.loads(extracted_text)
                logger.info("Successfully extracted attributes from PDF text")
                return extracted_data
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the text
                extracted_data = self._extract_json_from_text(extracted_text)
                return extracted_data
                
        except ClientError as e:
            logger.error(f"AWS Bedrock API error: {str(e)}")
            return self._get_empty_attributes_response(attributes_config)
        except Exception as e:
            logger.error(f"Error in attribute extraction: {str(e)}")
            return self._get_empty_attributes_response(attributes_config)
    
    def chatbot_response(self, user_input: str, context_data: Dict[str, Any]) -> str:
        """
        Generate chatbot response based on user input and extracted financial data
        
        Args:
            user_input: User's question or observation
            context_data: Extracted financial data for context
            
        Returns:
            Chatbot response string
        """
        try:
            # Prepare system prompt for chatbot
            system_prompt = """
            You are a financial analysis assistant with access to extracted financial data from PDF documents.
            Help users understand and analyze the financial information by:
            1. Answering questions about specific financial metrics
            2. Providing insights on trends and patterns
            3. Explaining financial ratios and their implications
            4. Comparing data across different periods
            5. Identifying potential areas of concern or opportunity
            
            Always base your responses on the provided data and be clear about any limitations.
            Be concise but informative in your responses.
            """
            
            # Prepare context information
            context_summary = self._prepare_context_summary(context_data)
            
            user_message = f"""
            Context Data:
            {context_summary}
            
            User Question/Observation:
            {user_input}
            
            Please provide a helpful response based on the available financial data.
            """
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.3,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            chatbot_response = response_body['content'][0]['text']
            
            logger.info("Generated chatbot response successfully")
            return chatbot_response
            
        except Exception as e:
            logger.error(f"Error generating chatbot response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later."
    
    def _build_extraction_system_prompt(self, attributes_config: List[Dict]) -> str:
        """Build system prompt for attribute extraction"""
        attributes_description = "\n".join([
            f"- {attr['name']}: {attr['description']} (Type: {attr['data_type']}, Required: {attr['required']})"
            for attr in attributes_config
        ])
        
        return f"""
        You are a financial document analysis expert. Your task is to extract specific financial attributes from document text.
        
        Extract the following attributes:
        {attributes_description}
        
        Return the results in this exact JSON format:
        {{
            "extraction_metadata": {{
                "processing_date": "YYYY-MM-DD",
                "confidence_score": 0.95,
                "extraction_method": "bedrock_claude",
                "confidence_calculation": {{
                    "text_clarity": 0.95,
                    "attribute_match": 0.90,
                    "context_relevance": 0.98,
                    "data_consistency": 0.92
                }}
            }},
            "extracted_attributes": {{
                "attribute_name": {{
                    "value": "extracted_value_or_null",
                    "confidence": 0.95,
                    "confidence_breakdown": {{
                        "text_clarity": 0.95,
                        "exact_match": 0.90,
                        "context_match": 0.98,
                        "format_validity": 0.92
                    }},
                    "source_text": "relevant_text_snippet",
                    "extraction_reasoning": "Brief explanation of why this value was selected"
                }}
            }}
        }}
        
        CONFIDENCE SCORING GUIDELINES:
        
        For each attribute, calculate confidence based on these factors:
        
        1. TEXT_CLARITY (0.0-1.0): How clear and readable is the source text?
           - 1.0: Perfect, clear text with no ambiguity
           - 0.8-0.9: Minor formatting issues or slight ambiguity
           - 0.6-0.7: Some OCR errors or unclear formatting
           - 0.4-0.5: Significant text quality issues
           - 0.0-0.3: Very poor text quality or unreadable
        
        2. EXACT_MATCH (0.0-1.0): How well does the found text match the attribute description?
           - 1.0: Perfect match with expected attribute name/label
           - 0.8-0.9: Close match with minor variations in terminology
           - 0.6-0.7: Reasonable match but requires interpretation
           - 0.4-0.5: Weak match, significant interpretation needed
           - 0.0-0.3: Very weak or no clear match
        
        3. CONTEXT_MATCH (0.0-1.0): Is the value found in the right context/section?
           - 1.0: Found in perfect context (e.g., income statement for revenue)
           - 0.8-0.9: Found in appropriate section with minor context issues
           - 0.6-0.7: Found in reasonable context but not ideal location
           - 0.4-0.5: Found in questionable context
           - 0.0-0.3: Found in wrong context or no clear context
        
        4. FORMAT_VALIDITY (0.0-1.0): Is the extracted value in the expected format?
           - 1.0: Perfect format (e.g., proper number format for currency)
           - 0.8-0.9: Minor format issues but clearly interpretable
           - 0.6-0.7: Some format issues requiring normalization
           - 0.4-0.5: Significant format problems
           - 0.0-0.3: Invalid or unrecognizable format
        
        OVERALL CONFIDENCE CALCULATION:
        confidence = (text_clarity * 0.25) + (exact_match * 0.30) + (context_match * 0.25) + (format_validity * 0.20)
        
        EXTRACTION GUIDELINES:
        - For currency values, extract numbers only (no currency symbols)
        - For dates, use YYYY-MM-DD format
        - If an attribute cannot be found, set value to null and confidence to 0
        - Always provide confidence scores between 0 and 1
        - Include relevant source text snippets for verification
        - Provide brief reasoning for each extraction
        """
    
    def _prepare_context_summary(self, context_data: Dict[str, Any]) -> str:
        """Prepare context summary for chatbot"""
        if not context_data:
            return "No financial data available."
        
        summary_parts = []
        
        # Add basic financial metrics if available
        if 'consolidated_data' in context_data:
            data = context_data['consolidated_data']
            summary_parts.append(f"Available data from {len(data)} PDF documents")
            
            # Add sample metrics
            if data:
                sample = data[0] if isinstance(data, list) else data
                if 'extracted_attributes' in sample:
                    attrs = sample['extracted_attributes']
                    summary_parts.append("Key metrics include:")
                    for attr_name, attr_data in attrs.items():
                        if attr_data.get('value') is not None:
                            summary_parts.append(f"- {attr_name}: {attr_data['value']}")
        
        return "\n".join(summary_parts) if summary_parts else "Financial data is available for analysis."
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response if direct parsing fails"""
        try:
            # Look for JSON-like content between curly braces
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.warning("Could not find JSON in response text")
                return {"error": "Failed to parse JSON response"}
                
        except Exception as e:
            logger.error(f"Failed to extract JSON from text: {str(e)}")
            return {"error": "Failed to parse response"}
    
    def _get_empty_attributes_response(self, attributes_config: List[Dict]) -> Dict[str, Any]:
        """Return empty response structure when extraction fails"""
        empty_attributes = {}
        for attr in attributes_config:
            empty_attributes[attr['name']] = {
                "value": None,
                "confidence": 0.0,
                "source_text": ""
            }
        
        return {
            "extraction_metadata": {
                "processing_date": "",
                "confidence_score": 0.0,
                "extraction_method": "bedrock_claude",
                "error": "Extraction failed"
            },
            "extracted_attributes": empty_attributes
        }
