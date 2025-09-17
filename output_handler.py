import boto3
import json
import logging
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
from botocore.exceptions import ClientError
from excel_generator import ExcelReportGenerator
import tempfile

logger = logging.getLogger(__name__)

class OutputHandler:
    """Handle saving outputs to S3 and generating download links"""
    
    def __init__(self, region_name: str = None):
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.output_bucket = os.getenv('S3_OUTPUT_BUCKET')
        
        if not self.output_bucket:
            raise ValueError("S3_OUTPUT_BUCKET environment variable is required")
        
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.getenv('AWS_SESSION_TOKEN')
            )
            logger.info(f"S3 client initialized for output bucket: {self.output_bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
        
        self.excel_generator = ExcelReportGenerator()
    
    def save_individual_json(self, pdf_data: Dict[str, Any], pdf_filename: str) -> str:
        """
        Save individual PDF extraction results as JSON to S3
        
        Args:
            pdf_data: Extracted data from PDF
            pdf_filename: Original PDF filename
            
        Returns:
            S3 key of saved JSON file
        """
        try:
            # Generate JSON filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(pdf_filename)[0]
            json_filename = f"{base_name}_{timestamp}.json"
            s3_key = f"Output/individual_jsons/{json_filename}"
            
            # Prepare JSON data with metadata
            json_output = {
                "metadata": {
                    "original_filename": pdf_filename,
                    "processing_timestamp": datetime.now().isoformat(),
                    "extraction_method": pdf_data.get('extraction_method', 'unknown'),
                    "processing_time_seconds": pdf_data.get('processing_time', 0),
                    "confidence_score": pdf_data.get('extraction_metadata', {}).get('confidence_score', 0)
                },
                "extraction_results": pdf_data.get('extracted_attributes', {}),
                "processing_details": {
                    "page_count": pdf_data.get('page_count', 0),
                    "has_text": pdf_data.get('has_text', False),
                    "has_images": pdf_data.get('has_images', False),
                    "errors": pdf_data.get('errors', [])
                }
            }
            
            # Convert to JSON string
            json_content = json.dumps(json_output, indent=2, default=str)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.output_bucket,
                Key=s3_key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'original-filename': pdf_filename,
                    'processing-timestamp': datetime.now().isoformat(),
                    'content-type': 'extraction-results'
                }
            )
            
            logger.info(f"Saved individual JSON: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error saving JSON to S3: {str(e)}")
            raise Exception(f"Failed to save JSON for {pdf_filename}")
        except Exception as e:
            logger.error(f"Unexpected error saving JSON: {str(e)}")
            raise
    
    def save_consolidated_excel(self, all_pdf_data: List[Dict[str, Any]]) -> str:
        """
        Save consolidated Excel report to S3
        
        Args:
            all_pdf_data: List of all PDF extraction results
            
        Returns:
            S3 key of saved Excel file
        """
        try:
            # Generate Excel filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_filename = f"consolidated_financial_report_{timestamp}.xlsx"
            s3_key = f"Output/consolidated_reports/{excel_filename}"
            
            # Generate Excel report
            excel_bytes = self.excel_generator.generate_consolidated_excel_report(all_pdf_data)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.output_bucket,
                Key=s3_key,
                Body=excel_bytes,
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                Metadata={
                    'report-type': 'consolidated-financial-report',
                    'processing-timestamp': datetime.now().isoformat(),
                    'pdf-count': str(len(all_pdf_data)),
                    'content-type': 'excel-report'
                }
            )
            
            logger.info(f"Saved consolidated Excel report: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error saving Excel report: {str(e)}")
            raise Exception("Failed to save consolidated Excel report")
    
    def process_and_save_all_outputs(self, pdf_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process and save all outputs (individual JSONs and consolidated Excel)
        
        Args:
            pdf_results: List of PDF processing results
            
        Returns:
            Dictionary containing all saved file information and download links
        """
        try:
            output_summary = {
                "processing_timestamp": datetime.now().isoformat(),
                "total_pdfs_processed": len(pdf_results),
                "individual_jsons": [],
                "consolidated_excel": None,
                "download_links": {},
                "processing_summary": {
                    "successful_extractions": 0,
                    "failed_extractions": 0,
                    "average_confidence": 0.0
                }
            }
            
            # Save individual JSON files
            successful_extractions = 0
            total_confidence = 0
            
            for pdf_result in pdf_results:
                try:
                    json_key = self.save_individual_json(pdf_result, pdf_result.get('filename', 'unknown.pdf'))
                    
                    json_info = {
                        "filename": pdf_result.get('filename'),
                        "s3_key": json_key,
                        "confidence_score": pdf_result.get('extraction_metadata', {}).get('confidence_score', 0),
                        "processing_time": pdf_result.get('processing_time', 0)
                    }
                    
                    output_summary["individual_jsons"].append(json_info)
                    
                    # Update statistics
                    confidence = pdf_result.get('extraction_metadata', {}).get('confidence_score', 0)
                    if confidence > 0.5:
                        successful_extractions += 1
                    total_confidence += confidence
                    
                except Exception as e:
                    logger.error(f"Failed to save JSON for {pdf_result.get('filename')}: {str(e)}")
                    output_summary["individual_jsons"].append({
                        "filename": pdf_result.get('filename'),
                        "s3_key": None,
                        "error": str(e)
                    })
            
            # Update processing summary
            output_summary["processing_summary"].update({
                "successful_extractions": successful_extractions,
                "failed_extractions": len(pdf_results) - successful_extractions,
                "average_confidence": total_confidence / len(pdf_results) if pdf_results else 0
            })
            
            # Save consolidated Excel report
            try:
                excel_key = self.save_consolidated_excel(pdf_results)
                output_summary["consolidated_excel"] = {
                    "s3_key": excel_key,
                    "filename": os.path.basename(excel_key)
                }
            except Exception as e:
                logger.error(f"Failed to save consolidated Excel: {str(e)}")
                output_summary["consolidated_excel"] = {
                    "s3_key": None,
                    "error": str(e)
                }
            
            # Generate download links
            output_summary["download_links"] = self.generate_download_links(output_summary)
            
            logger.info(f"Completed processing all outputs. Success rate: {successful_extractions}/{len(pdf_results)}")
            return output_summary
            
        except Exception as e:
            logger.error(f"Error in process_and_save_all_outputs: {str(e)}")
            raise
    
    def generate_download_links(self, output_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate presigned URLs for downloading files
        
        Args:
            output_summary: Summary of all saved outputs
            
        Returns:
            Dictionary containing download links
        """
        download_links = {
            "individual_jsons": [],
            "consolidated_excel": None,
            "expiration_time": "24 hours"
        }
        
        try:
            # Generate links for individual JSON files
            for json_info in output_summary.get("individual_jsons", []):
                if json_info.get("s3_key"):
                    try:
                        presigned_url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={
                                'Bucket': self.output_bucket,
                                'Key': json_info["s3_key"]
                            },
                            ExpiresIn=86400  # 24 hours
                        )
                        
                        download_links["individual_jsons"].append({
                            "filename": json_info["filename"],
                            "download_url": presigned_url,
                            "confidence_score": json_info.get("confidence_score", 0)
                        })
                        
                    except Exception as e:
                        logger.error(f"Failed to generate download link for {json_info['filename']}: {str(e)}")
            
            # Generate link for consolidated Excel
            excel_info = output_summary.get("consolidated_excel")
            if excel_info and excel_info.get("s3_key"):
                try:
                    presigned_url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': self.output_bucket,
                            'Key': excel_info["s3_key"]
                        },
                        ExpiresIn=86400  # 24 hours
                    )
                    
                    download_links["consolidated_excel"] = {
                        "filename": excel_info["filename"],
                        "download_url": presigned_url
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to generate download link for Excel report: {str(e)}")
            
            logger.info(f"Generated {len(download_links['individual_jsons'])} JSON download links and Excel link")
            return download_links
            
        except Exception as e:
            logger.error(f"Error generating download links: {str(e)}")
            return download_links
    
    def list_previous_outputs(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List previously generated outputs in S3
        
        Returns:
            Dictionary containing lists of previous outputs
        """
        try:
            previous_outputs = {
                "individual_jsons": [],
                "consolidated_reports": []
            }
            
            # List individual JSON files
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.output_bucket,
                    Prefix="Output/individual_jsons/"
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if obj['Key'].endswith('.json'):
                            previous_outputs["individual_jsons"].append({
                                "key": obj['Key'],
                                "filename": os.path.basename(obj['Key']),
                                "size": obj['Size'],
                                "last_modified": obj['LastModified'],
                                "size_kb": round(obj['Size'] / 1024, 2)
                            })
            except Exception as e:
                logger.warning(f"Could not list individual JSONs: {str(e)}")
            
            # List consolidated reports
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.output_bucket,
                    Prefix="Output/consolidated_reports/"
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if obj['Key'].endswith('.xlsx'):
                            previous_outputs["consolidated_reports"].append({
                                "key": obj['Key'],
                                "filename": os.path.basename(obj['Key']),
                                "size": obj['Size'],
                                "last_modified": obj['LastModified'],
                                "size_mb": round(obj['Size'] / (1024 * 1024), 2)
                            })
            except Exception as e:
                logger.warning(f"Could not list consolidated reports: {str(e)}")
            
            # Sort by last modified (newest first)
            previous_outputs["individual_jsons"].sort(key=lambda x: x['last_modified'], reverse=True)
            previous_outputs["consolidated_reports"].sort(key=lambda x: x['last_modified'], reverse=True)
            
            return previous_outputs
            
        except Exception as e:
            logger.error(f"Error listing previous outputs: {str(e)}")
            return {"individual_jsons": [], "consolidated_reports": []}
    
    def cleanup_old_outputs(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old output files from S3
        
        Args:
            days_to_keep: Number of days to keep files
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleanup_stats = {
                "files_deleted": 0,
                "space_freed_mb": 0,
                "errors": 0
            }
            
            # List all output files
            response = self.s3_client.list_objects_v2(
                Bucket=self.output_bucket,
                Prefix="Output/"
            )
            
            if 'Contents' in response:
                files_to_delete = []
                
                for obj in response['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        files_to_delete.append({'Key': obj['Key']})
                        cleanup_stats["space_freed_mb"] += obj['Size'] / (1024 * 1024)
                
                # Delete old files in batches
                if files_to_delete:
                    for i in range(0, len(files_to_delete), 1000):  # S3 delete limit is 1000
                        batch = files_to_delete[i:i+1000]
                        try:
                            self.s3_client.delete_objects(
                                Bucket=self.output_bucket,
                                Delete={'Objects': batch}
                            )
                            cleanup_stats["files_deleted"] += len(batch)
                        except Exception as e:
                            logger.error(f"Error deleting batch: {str(e)}")
                            cleanup_stats["errors"] += len(batch)
            
            logger.info(f"Cleanup completed: {cleanup_stats['files_deleted']} files deleted, "
                       f"{cleanup_stats['space_freed_mb']:.2f}MB freed")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {"files_deleted": 0, "space_freed_mb": 0, "errors": 1}
