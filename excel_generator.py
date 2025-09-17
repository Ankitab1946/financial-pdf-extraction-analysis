import pandas as pd
import xlsxwriter
from io import BytesIO
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ExcelReportGenerator:
    """Generate comprehensive Excel reports from extracted PDF data"""
    
    def __init__(self):
        self.workbook = None
        self.worksheet_formats = {}
    
    def generate_consolidated_excel_report(self, json_data_list: List[Dict[str, Any]]) -> bytes:
        """
        Generate comprehensive Excel report with multiple sheets
        
        Args:
            json_data_list: List of extracted data from all PDFs
            
        Returns:
            Excel file as bytes
        """
        try:
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                self.workbook = writer.book
                self._setup_formats()
                
                # Prepare consolidated data
                consolidated_data = self._prepare_consolidated_data(json_data_list)
                
                # Generate all sheets
                self._create_summary_dashboard(consolidated_data, writer)
                self._create_consolidated_data_sheet(consolidated_data, writer)
                self._create_yoy_analysis_sheet(consolidated_data, writer)
                self._create_monthly_breakdown_sheet(consolidated_data, writer)
                self._create_individual_pdf_sheets(json_data_list, writer)
                self._create_data_quality_report(json_data_list, writer)
                
                # Apply final formatting
                self._apply_workbook_formatting(writer)
            
            output.seek(0)
            excel_bytes = output.getvalue()
            
            logger.info(f"Generated Excel report with {len(json_data_list)} PDF data entries")
            return excel_bytes
            
        except Exception as e:
            logger.error(f"Error generating Excel report: {str(e)}")
            raise
    
    def _setup_formats(self):
        """Setup Excel formatting styles"""
        self.worksheet_formats = {
            'header': self.workbook.add_format({
                'bold': True,
                'font_color': 'white',
                'bg_color': '#4472C4',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': 'Calibri',
                'font_size': 11
            }),
            'subheader': self.workbook.add_format({
                'bold': True,
                'bg_color': '#D9E2F3',
                'border': 1,
                'align': 'center',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'data': self.workbook.add_format({
                'border': 1,
                'align': 'left',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'number': self.workbook.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '#,##0',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'currency': self.workbook.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '$#,##0',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'percentage': self.workbook.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '0.00%',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'date': self.workbook.add_format({
                'border': 1,
                'align': 'center',
                'num_format': 'yyyy-mm-dd',
                'font_name': 'Calibri',
                'font_size': 10
            }),
            'highlight': self.workbook.add_format({
                'bg_color': '#FFE699',
                'border': 1,
                'font_name': 'Calibri',
                'font_size': 10
            })
        }
    
    def _prepare_consolidated_data(self, json_data_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare consolidated data from all PDFs"""
        consolidated_rows = []
        
        for pdf_data in json_data_list:
            if 'extracted_attributes' not in pdf_data:
                continue
                
            base_info = {
                'PDF_Name': pdf_data.get('filename', 'Unknown'),
                'Processing_Date': pdf_data.get('extraction_metadata', {}).get('processing_date', ''),
                'Overall_Confidence': pdf_data.get('extraction_metadata', {}).get('confidence_score', 0)
            }
            
            # Extract attributes
            attributes = pdf_data['extracted_attributes']
            row_data = base_info.copy()
            
            for attr_name, attr_data in attributes.items():
                if isinstance(attr_data, dict):
                    row_data[attr_name] = attr_data.get('value')
                    row_data[f"{attr_name}_Confidence"] = attr_data.get('confidence', 0)
                else:
                    row_data[attr_name] = attr_data
                    row_data[f"{attr_name}_Confidence"] = 0
            
            consolidated_rows.append(row_data)
        
        return pd.DataFrame(consolidated_rows)
    
    def _create_summary_dashboard(self, consolidated_data: pd.DataFrame, writer):
        """Create summary dashboard sheet"""
        worksheet = writer.book.add_worksheet('Summary Dashboard')
        
        # Title
        worksheet.merge_range('A1:F1', 'Financial Data Extraction Summary', self.worksheet_formats['header'])
        
        # Summary statistics
        row = 3
        summary_data = [
            ['Total PDFs Processed', len(consolidated_data)],
            ['Processing Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Average Confidence Score', f"{consolidated_data['Overall_Confidence'].mean():.2%}" if not consolidated_data.empty else "N/A"]
        ]
        
        # Add date range if available
        if 'Report Year' in consolidated_data.columns:
            years = consolidated_data['Report Year'].dropna()
            if not years.empty:
                summary_data.extend([
                    ['Year Range', f"{years.min()} - {years.max()}"],
                    ['Unique Years', len(years.unique())]
                ])
        
        # Write summary data
        for i, (label, value) in enumerate(summary_data):
            worksheet.write(row + i, 0, label, self.worksheet_formats['subheader'])
            worksheet.write(row + i, 1, value, self.worksheet_formats['data'])
        
        # Key metrics summary
        if not consolidated_data.empty:
            row += len(summary_data) + 2
            worksheet.write(row, 0, 'Key Financial Metrics Summary', self.worksheet_formats['header'])
            row += 1
            
            financial_columns = ['Total Revenue', 'Net Income', 'Total Assets', 'Total Liabilities']
            metrics_data = []
            
            for col in financial_columns:
                if col in consolidated_data.columns:
                    values = pd.to_numeric(consolidated_data[col], errors='coerce').dropna()
                    if not values.empty:
                        metrics_data.append([
                            col,
                            f"${values.sum():,.0f}",
                            f"${values.mean():,.0f}",
                            f"${values.min():,.0f}",
                            f"${values.max():,.0f}"
                        ])
            
            if metrics_data:
                headers = ['Metric', 'Total', 'Average', 'Minimum', 'Maximum']
                for i, header in enumerate(headers):
                    worksheet.write(row, i, header, self.worksheet_formats['subheader'])
                
                for i, metric_row in enumerate(metrics_data):
                    for j, value in enumerate(metric_row):
                        worksheet.write(row + 1 + i, j, value, self.worksheet_formats['data'])
        
        # Auto-fit columns
        worksheet.set_column('A:F', 20)
    
    def _create_consolidated_data_sheet(self, consolidated_data: pd.DataFrame, writer):
        """Create consolidated data sheet"""
        if consolidated_data.empty:
            return
        
        # Write to Excel with formatting
        consolidated_data.to_excel(writer, sheet_name='Consolidated Data', index=False, startrow=1)
        
        worksheet = writer.sheets['Consolidated Data']
        
        # Add title
        worksheet.merge_range(0, 0, 0, len(consolidated_data.columns)-1, 
                            'Consolidated Financial Data', self.worksheet_formats['header'])
        
        # Format headers
        for col_num, column in enumerate(consolidated_data.columns):
            worksheet.write(1, col_num, column, self.worksheet_formats['subheader'])
        
        # Format data based on column type
        for col_num, column in enumerate(consolidated_data.columns):
            if 'Revenue' in column or 'Income' in column or 'Assets' in column or 'Liabilities' in column:
                worksheet.set_column(col_num, col_num, 15, self.worksheet_formats['currency'])
            elif 'Confidence' in column:
                worksheet.set_column(col_num, col_num, 12, self.worksheet_formats['percentage'])
            elif 'Date' in column:
                worksheet.set_column(col_num, col_num, 12, self.worksheet_formats['date'])
            else:
                worksheet.set_column(col_num, col_num, 15, self.worksheet_formats['data'])
        
        # Add filters
        worksheet.autofilter(1, 0, len(consolidated_data), len(consolidated_data.columns)-1)
        
        # Freeze panes
        worksheet.freeze_panes(2, 1)
    
    def _create_yoy_analysis_sheet(self, consolidated_data: pd.DataFrame, writer):
        """Create year-over-year analysis sheet"""
        if consolidated_data.empty or 'Report Year' not in consolidated_data.columns:
            return
        
        worksheet = writer.book.add_worksheet('Year-over-Year Analysis')
        
        # Title
        worksheet.merge_range('A1:F1', 'Year-over-Year Financial Analysis', self.worksheet_formats['header'])
        
        # Group data by year
        yearly_data = consolidated_data.groupby('Report Year').agg({
            'Total Revenue': 'sum',
            'Net Income': 'sum',
            'Total Assets': 'mean',
            'Total Liabilities': 'mean'
        }).fillna(0)
        
        if len(yearly_data) < 2:
            worksheet.write(3, 0, 'Insufficient data for year-over-year analysis', self.worksheet_formats['data'])
            return
        
        # Calculate year-over-year changes
        yoy_changes = yearly_data.pct_change().fillna(0)
        
        # Write yearly data
        row = 3
        worksheet.write(row, 0, 'Year', self.worksheet_formats['subheader'])
        for col_num, column in enumerate(yearly_data.columns, 1):
            worksheet.write(row, col_num, column, self.worksheet_formats['subheader'])
        
        for year_idx, (year, data) in enumerate(yearly_data.iterrows()):
            worksheet.write(row + 1 + year_idx, 0, int(year), self.worksheet_formats['data'])
            for col_num, value in enumerate(data, 1):
                worksheet.write(row + 1 + year_idx, col_num, value, self.worksheet_formats['currency'])
        
        # Write YoY changes
        row += len(yearly_data) + 3
        worksheet.write(row, 0, 'Year-over-Year Growth (%)', self.worksheet_formats['header'])
        row += 1
        
        worksheet.write(row, 0, 'Year', self.worksheet_formats['subheader'])
        for col_num, column in enumerate(yoy_changes.columns, 1):
            worksheet.write(row, col_num, f"{column} Growth", self.worksheet_formats['subheader'])
        
        for year_idx, (year, changes) in enumerate(yoy_changes.iterrows()):
            if year_idx == 0:  # Skip first year (no previous year to compare)
                continue
            worksheet.write(row + year_idx, 0, int(year), self.worksheet_formats['data'])
            for col_num, change in enumerate(changes, 1):
                worksheet.write(row + year_idx, col_num, change, self.worksheet_formats['percentage'])
        
        # Auto-fit columns
        worksheet.set_column('A:F', 18)
    
    def _create_monthly_breakdown_sheet(self, consolidated_data: pd.DataFrame, writer):
        """Create monthly breakdown sheet"""
        if consolidated_data.empty:
            return
        
        worksheet = writer.book.add_worksheet('Monthly Breakdown')
        
        # Title
        worksheet.merge_range('A1:F1', 'Monthly Financial Breakdown', self.worksheet_formats['header'])
        
        # Group by quarter if available
        if 'Report Quarter' in consolidated_data.columns:
            quarterly_data = consolidated_data.groupby(['Report Year', 'Report Quarter']).agg({
                'Total Revenue': 'sum',
                'Net Income': 'sum',
                'Total Assets': 'mean'
            }).fillna(0)
            
            row = 3
            headers = ['Year', 'Quarter', 'Total Revenue', 'Net Income', 'Total Assets']
            for col_num, header in enumerate(headers):
                worksheet.write(row, col_num, header, self.worksheet_formats['subheader'])
            
            for idx, ((year, quarter), data) in enumerate(quarterly_data.iterrows()):
                worksheet.write(row + 1 + idx, 0, int(year), self.worksheet_formats['data'])
                worksheet.write(row + 1 + idx, 1, quarter, self.worksheet_formats['data'])
                for col_num, value in enumerate(data, 2):
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['currency'])
        else:
            worksheet.write(3, 0, 'No quarterly data available for breakdown', self.worksheet_formats['data'])
        
        # Auto-fit columns
        worksheet.set_column('A:F', 15)
    
    def _create_individual_pdf_sheets(self, json_data_list: List[Dict[str, Any]], writer):
        """Create individual PDF details sheet"""
        worksheet = writer.book.add_worksheet('Individual PDF Details')
        
        # Title
        worksheet.merge_range('A1:H1', 'Individual PDF Processing Details', self.worksheet_formats['header'])
        
        # Headers
        headers = ['PDF Name', 'Processing Date', 'Page Count', 'Extraction Method', 
                  'Processing Time (s)', 'Confidence Score', 'Has Text', 'Errors']
        
        row = 3
        for col_num, header in enumerate(headers):
            worksheet.write(row, col_num, header, self.worksheet_formats['subheader'])
        
        # Data
        for idx, pdf_data in enumerate(json_data_list):
            data_row = [
                pdf_data.get('filename', 'Unknown'),
                pdf_data.get('extraction_metadata', {}).get('processing_date', ''),
                pdf_data.get('page_count', 0),
                pdf_data.get('extraction_method', ''),
                pdf_data.get('processing_time', 0),
                pdf_data.get('extraction_metadata', {}).get('confidence_score', 0),
                'Yes' if pdf_data.get('has_text', False) else 'No',
                '; '.join(pdf_data.get('errors', []))
            ]
            
            for col_num, value in enumerate(data_row):
                if col_num == 5:  # Confidence score
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['percentage'])
                elif col_num == 4:  # Processing time
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['number'])
                else:
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['data'])
        
        # Auto-fit columns
        worksheet.set_column('A:H', 15)
    
    def _create_data_quality_report(self, json_data_list: List[Dict[str, Any]], writer):
        """Create data quality report sheet"""
        worksheet = writer.book.add_worksheet('Data Quality Report')
        
        # Title
        worksheet.merge_range('A1:H1', 'Data Quality Assessment & Confidence Analysis', self.worksheet_formats['header'])
        
        # Calculate quality metrics
        total_pdfs = len(json_data_list)
        successful_extractions = sum(1 for pdf in json_data_list 
                                   if pdf.get('extraction_metadata', {}).get('confidence_score', 0) > 0.5)
        
        avg_confidence = sum(pdf.get('extraction_metadata', {}).get('confidence_score', 0) 
                           for pdf in json_data_list) / total_pdfs if total_pdfs > 0 else 0
        
        # Quality summary
        row = 3
        quality_data = [
            ['Total PDFs Processed', total_pdfs],
            ['Successful Extractions', successful_extractions],
            ['Success Rate', f"{(successful_extractions/total_pdfs)*100:.1f}%" if total_pdfs > 0 else "0%"],
            ['Average Confidence Score', f"{avg_confidence:.2%}"],
            ['Processing Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        for i, (label, value) in enumerate(quality_data):
            worksheet.write(row + i, 0, label, self.worksheet_formats['subheader'])
            worksheet.write(row + i, 1, value, self.worksheet_formats['data'])
        
        # Confidence Score Calculation Explanation
        row += len(quality_data) + 2
        worksheet.write(row, 0, 'Confidence Score Calculation Method', self.worksheet_formats['header'])
        row += 1
        
        confidence_explanation = [
            ['Component', 'Weight', 'Description'],
            ['Text Clarity', '25%', 'How clear and readable is the source text'],
            ['Exact Match', '30%', 'How well the found text matches the attribute description'],
            ['Context Match', '25%', 'Whether the value is found in the right context/section'],
            ['Format Validity', '20%', 'Whether the extracted value is in the expected format'],
            ['', '', ''],
            ['Formula:', '', 'confidence = (text_clarity × 0.25) + (exact_match × 0.30) + (context_match × 0.25) + (format_validity × 0.20)']
        ]
        
        for i, (component, weight, description) in enumerate(confidence_explanation):
            worksheet.write(row + i, 0, component, self.worksheet_formats['subheader'] if i == 0 else self.worksheet_formats['data'])
            worksheet.write(row + i, 1, weight, self.worksheet_formats['subheader'] if i == 0 else self.worksheet_formats['data'])
            worksheet.write(row + i, 2, description, self.worksheet_formats['subheader'] if i == 0 else self.worksheet_formats['data'])
        
        # Detailed quality metrics per PDF
        row += len(confidence_explanation) + 2
        worksheet.write(row, 0, 'Detailed Quality Metrics per PDF', self.worksheet_formats['header'])
        row += 1
        
        detail_headers = ['PDF Name', 'Overall Confidence', 'Text Clarity', 'Exact Match', 'Context Match', 'Format Validity', 'Extraction Method', 'Issues']
        for col_num, header in enumerate(detail_headers):
            worksheet.write(row, col_num, header, self.worksheet_formats['subheader'])
        
        for idx, pdf_data in enumerate(json_data_list):
            confidence = pdf_data.get('extraction_metadata', {}).get('confidence_score', 0)
            confidence_calc = pdf_data.get('extraction_metadata', {}).get('confidence_calculation', {})
            
            issues = []
            if confidence < 0.5:
                issues.append('Low confidence')
            if pdf_data.get('errors'):
                issues.append('Processing errors')
            if not pdf_data.get('has_text', False):
                issues.append('No text detected')
            
            detail_row = [
                pdf_data.get('filename', 'Unknown'),
                confidence,
                confidence_calc.get('text_clarity', 0),
                confidence_calc.get('attribute_match', 0),
                confidence_calc.get('context_relevance', 0),
                confidence_calc.get('data_consistency', 0),
                pdf_data.get('extraction_method', ''),
                '; '.join(issues) if issues else 'None'
            ]
            
            for col_num, value in enumerate(detail_row):
                if col_num in [1, 2, 3, 4, 5]:  # Confidence scores
                    cell_format = self.worksheet_formats['highlight'] if (isinstance(value, (int, float)) and value < 0.5) else self.worksheet_formats['percentage']
                    worksheet.write(row + 1 + idx, col_num, value, cell_format)
                else:
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['data'])
        
        # Attribute-level confidence analysis
        row += len(json_data_list) + 3
        worksheet.write(row, 0, 'Attribute-Level Confidence Analysis', self.worksheet_formats['header'])
        row += 1
        
        # Collect all attributes and their confidence scores
        attribute_confidence = {}
        for pdf_data in json_data_list:
            extracted_attrs = pdf_data.get('extracted_attributes', {})
            for attr_name, attr_data in extracted_attrs.items():
                if attr_name not in attribute_confidence:
                    attribute_confidence[attr_name] = []
                
                if isinstance(attr_data, dict):
                    confidence = attr_data.get('confidence', 0)
                    confidence_breakdown = attr_data.get('confidence_breakdown', {})
                    attribute_confidence[attr_name].append({
                        'confidence': confidence,
                        'breakdown': confidence_breakdown
                    })
        
        # Create attribute confidence summary
        attr_headers = ['Attribute', 'Avg Confidence', 'Min Confidence', 'Max Confidence', 'Avg Text Clarity', 'Avg Exact Match', 'Avg Context Match', 'Avg Format Validity']
        for col_num, header in enumerate(attr_headers):
            worksheet.write(row, col_num, header, self.worksheet_formats['subheader'])
        
        for idx, (attr_name, confidence_data) in enumerate(attribute_confidence.items()):
            if not confidence_data:
                continue
                
            confidences = [item['confidence'] for item in confidence_data]
            avg_confidence = sum(confidences) / len(confidences)
            min_confidence = min(confidences)
            max_confidence = max(confidences)
            
            # Calculate average breakdown scores
            text_clarity_scores = [item['breakdown'].get('text_clarity', 0) for item in confidence_data if item['breakdown']]
            exact_match_scores = [item['breakdown'].get('exact_match', 0) for item in confidence_data if item['breakdown']]
            context_match_scores = [item['breakdown'].get('context_match', 0) for item in confidence_data if item['breakdown']]
            format_validity_scores = [item['breakdown'].get('format_validity', 0) for item in confidence_data if item['breakdown']]
            
            avg_text_clarity = sum(text_clarity_scores) / len(text_clarity_scores) if text_clarity_scores else 0
            avg_exact_match = sum(exact_match_scores) / len(exact_match_scores) if exact_match_scores else 0
            avg_context_match = sum(context_match_scores) / len(context_match_scores) if context_match_scores else 0
            avg_format_validity = sum(format_validity_scores) / len(format_validity_scores) if format_validity_scores else 0
            
            attr_row = [
                attr_name,
                avg_confidence,
                min_confidence,
                max_confidence,
                avg_text_clarity,
                avg_exact_match,
                avg_context_match,
                avg_format_validity
            ]
            
            for col_num, value in enumerate(attr_row):
                if col_num == 0:  # Attribute name
                    worksheet.write(row + 1 + idx, col_num, value, self.worksheet_formats['data'])
                else:  # Confidence scores
                    cell_format = self.worksheet_formats['highlight'] if (isinstance(value, (int, float)) and value < 0.5) else self.worksheet_formats['percentage']
                    worksheet.write(row + 1 + idx, col_num, value, cell_format)
        
        # Auto-fit columns
        worksheet.set_column('A:H', 18)
    
    def _apply_workbook_formatting(self, writer):
        """Apply final workbook-level formatting"""
        # Set default font for all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.set_default_row(15)  # Set default row height
