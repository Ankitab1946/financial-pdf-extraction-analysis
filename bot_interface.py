import logging
from typing import Dict, Any, List, Optional
from bedrock_client import BedrockClient
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class BotInterface:
    """Chatbot interface for user observations and questions about extracted financial data"""
    
    def __init__(self, bedrock_client: BedrockClient = None):
        self.bedrock_client = bedrock_client or BedrockClient()
        self.conversation_history = []
        self.context_data = {}
        self.max_history_length = 10  # Keep last 10 exchanges
    
    def set_context_data(self, extracted_data: Dict[str, Any]):
        """
        Set the financial data context for the chatbot
        
        Args:
            extracted_data: Dictionary containing all extracted financial data
        """
        self.context_data = extracted_data
        logger.info("Updated chatbot context with new financial data")
    
    def handle_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and generate response
        
        Args:
            user_input: User's question or observation
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            # Validate input
            if not user_input or not user_input.strip():
                return {
                    "response": "Please provide a question or observation about the financial data.",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Empty input"
                }
            
            # Check if context data is available
            if not self.context_data:
                return {
                    "response": "I don't have any financial data to analyze yet. Please extract data from PDFs first.",
                    "timestamp": datetime.now().isoformat(),
                    "error": "No context data"
                }
            
            # Generate response using Bedrock
            response = self.bedrock_client.chatbot_response(user_input, self.context_data)
            
            # Store conversation in history
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "bot_response": response
            }
            
            self.conversation_history.append(conversation_entry)
            
            # Trim history if too long
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
            
            # Prepare response with additional context
            bot_response = {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "context_summary": self._get_context_summary(),
                "suggested_questions": self._get_suggested_questions(),
                "data_availability": self._check_data_availability()
            }
            
            logger.info(f"Generated bot response for user input: {user_input[:50]}...")
            return bot_response
            
        except Exception as e:
            logger.error(f"Error handling user input: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history
        
        Returns:
            List of conversation entries
        """
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
        logger.info("Cleared conversation history")
    
    def _get_context_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of available context data
        
        Returns:
            Dictionary containing context summary
        """
        if not self.context_data:
            return {"status": "No data available"}
        
        summary = {
            "status": "Data available",
            "pdf_count": 0,
            "date_range": "Unknown",
            "key_metrics_available": []
        }
        
        try:
            # Count PDFs
            if "consolidated_data" in self.context_data:
                consolidated = self.context_data["consolidated_data"]
                if isinstance(consolidated, list):
                    summary["pdf_count"] = len(consolidated)
                elif isinstance(consolidated, dict):
                    summary["pdf_count"] = 1
            
            # Check for common financial metrics
            common_metrics = [
                "Total Revenue", "Net Income", "Total Assets", "Total Liabilities",
                "Shareholders Equity", "Operating Cash Flow", "Gross Profit"
            ]
            
            available_metrics = []
            if "consolidated_data" in self.context_data:
                data = self.context_data["consolidated_data"]
                if isinstance(data, list) and data:
                    sample_data = data[0]
                    if "extracted_attributes" in sample_data:
                        for metric in common_metrics:
                            if metric in sample_data["extracted_attributes"]:
                                attr_data = sample_data["extracted_attributes"][metric]
                                if isinstance(attr_data, dict) and attr_data.get("value") is not None:
                                    available_metrics.append(metric)
                                elif attr_data is not None:
                                    available_metrics.append(metric)
            
            summary["key_metrics_available"] = available_metrics
            
            # Try to determine date range
            years = []
            if "consolidated_data" in self.context_data:
                data = self.context_data["consolidated_data"]
                if isinstance(data, list):
                    for item in data:
                        if "extracted_attributes" in item:
                            year_data = item["extracted_attributes"].get("Report Year")
                            if isinstance(year_data, dict):
                                year = year_data.get("value")
                            else:
                                year = year_data
                            
                            if year and str(year).isdigit():
                                years.append(int(year))
            
            if years:
                summary["date_range"] = f"{min(years)} - {max(years)}" if len(set(years)) > 1 else str(years[0])
            
        except Exception as e:
            logger.warning(f"Error generating context summary: {str(e)}")
            summary["error"] = "Could not analyze context data"
        
        return summary
    
    def _get_suggested_questions(self) -> List[str]:
        """
        Generate suggested questions based on available data
        
        Returns:
            List of suggested questions
        """
        if not self.context_data:
            return [
                "Please extract data from PDFs first to get started.",
                "Upload PDFs and run extraction to begin analysis."
            ]
        
        suggestions = []
        context_summary = self._get_context_summary()
        
        # Basic questions
        if context_summary.get("pdf_count", 0) > 0:
            suggestions.extend([
                "What is the total revenue across all periods?",
                "Show me the net income trends.",
                "What are the key financial ratios?"
            ])
        
        # Multi-period questions
        if context_summary.get("pdf_count", 0) > 1:
            suggestions.extend([
                "Compare revenue growth year over year.",
                "What are the biggest changes in financial position?",
                "Analyze the profitability trends."
            ])
        
        # Metric-specific questions
        available_metrics = context_summary.get("key_metrics_available", [])
        if "Total Assets" in available_metrics and "Total Liabilities" in available_metrics:
            suggestions.append("Calculate the debt-to-equity ratio.")
        
        if "Total Revenue" in available_metrics and "Net Income" in available_metrics:
            suggestions.append("What is the profit margin?")
        
        if "Operating Cash Flow" in available_metrics:
            suggestions.append("How is the cash flow performance?")
        
        # Limit to 5 suggestions
        return suggestions[:5]
    
    def _check_data_availability(self) -> Dict[str, Any]:
        """
        Check what types of data are available for analysis
        
        Returns:
            Dictionary describing data availability
        """
        availability = {
            "has_revenue_data": False,
            "has_profitability_data": False,
            "has_balance_sheet_data": False,
            "has_cash_flow_data": False,
            "has_multi_period_data": False,
            "data_quality": "unknown"
        }
        
        if not self.context_data:
            return availability
        
        try:
            consolidated_data = self.context_data.get("consolidated_data", [])
            if not isinstance(consolidated_data, list):
                consolidated_data = [consolidated_data] if consolidated_data else []
            
            if not consolidated_data:
                return availability
            
            # Check for multi-period data
            availability["has_multi_period_data"] = len(consolidated_data) > 1
            
            # Analyze available metrics
            all_attributes = set()
            confidence_scores = []
            
            for item in consolidated_data:
                if "extracted_attributes" in item:
                    attributes = item["extracted_attributes"]
                    all_attributes.update(attributes.keys())
                    
                    # Collect confidence scores
                    for attr_data in attributes.values():
                        if isinstance(attr_data, dict) and "confidence" in attr_data:
                            confidence_scores.append(attr_data["confidence"])
            
            # Check data categories
            revenue_indicators = ["Total Revenue", "Gross Profit", "Revenue"]
            profitability_indicators = ["Net Income", "EBITDA", "Operating Income"]
            balance_sheet_indicators = ["Total Assets", "Total Liabilities", "Shareholders Equity"]
            cash_flow_indicators = ["Operating Cash Flow", "Free Cash Flow", "Cash Flow"]
            
            availability["has_revenue_data"] = any(indicator in all_attributes for indicator in revenue_indicators)
            availability["has_profitability_data"] = any(indicator in all_attributes for indicator in profitability_indicators)
            availability["has_balance_sheet_data"] = any(indicator in all_attributes for indicator in balance_sheet_indicators)
            availability["has_cash_flow_data"] = any(indicator in all_attributes for indicator in cash_flow_indicators)
            
            # Assess data quality
            if confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                if avg_confidence >= 0.8:
                    availability["data_quality"] = "high"
                elif avg_confidence >= 0.6:
                    availability["data_quality"] = "medium"
                else:
                    availability["data_quality"] = "low"
            
        except Exception as e:
            logger.warning(f"Error checking data availability: {str(e)}")
            availability["error"] = str(e)
        
        return availability
    
    def generate_financial_insights(self) -> Dict[str, Any]:
        """
        Generate automatic financial insights from the available data
        
        Returns:
            Dictionary containing financial insights
        """
        if not self.context_data:
            return {"error": "No data available for analysis"}
        
        try:
            insights_prompt = """
            Based on the financial data provided, generate key insights including:
            1. Overall financial health assessment
            2. Notable trends or patterns
            3. Areas of strength and concern
            4. Key financial ratios and their implications
            5. Recommendations for further analysis
            
            Please provide a concise but comprehensive analysis.
            """
            
            response = self.bedrock_client.chatbot_response(insights_prompt, self.context_data)
            
            return {
                "insights": response,
                "timestamp": datetime.now().isoformat(),
                "data_summary": self._get_context_summary()
            }
            
        except Exception as e:
            logger.error(f"Error generating financial insights: {str(e)}")
            return {"error": f"Failed to generate insights: {str(e)}"}
    
    def export_conversation(self) -> Dict[str, Any]:
        """
        Export the conversation history for download
        
        Returns:
            Dictionary containing formatted conversation data
        """
        return {
            "export_timestamp": datetime.now().isoformat(),
            "conversation_count": len(self.conversation_history),
            "context_summary": self._get_context_summary(),
            "conversations": self.conversation_history
        }
