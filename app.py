import streamlit as st
import os
import logging
from dotenv import load_dotenv
import yaml
from typing import List

# Load environment variables first
load_dotenv()

# Import modules after loading environment
from pdf_processor import PDFProcessor
from bedrock_client import BedrockClient
from output_handler import OutputHandler
from bot_interface import BotInterface
from env_config import get_s3_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config.yaml
@st.cache_data
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

config = load_config()

# Initialize clients with proper error handling
@st.cache_resource
def initialize_clients():
    try:
        # Check S3 configuration
        s3_config = get_s3_config()
        
        if s3_config['use_single_bucket']:
            required_vars = ['S3_BUCKET_NAME', 'AWS_REGION']
            missing_vars = []
            if not os.getenv('S3_BUCKET_NAME'):
                missing_vars.append('S3_BUCKET_NAME')
        else:
            required_vars = ['S3_INPUT_BUCKET', 'S3_OUTPUT_BUCKET', 'AWS_REGION']
            missing_vars = []
            if not os.getenv('S3_INPUT_BUCKET'):
                missing_vars.append('S3_INPUT_BUCKET')
            if not os.getenv('S3_OUTPUT_BUCKET'):
                missing_vars.append('S3_OUTPUT_BUCKET')
        
        if not os.getenv('AWS_REGION'):
            missing_vars.append('AWS_REGION')
        
        if missing_vars:
            st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            st.info("Please set the following environment variables in your .env file:")
            
            if s3_config['use_single_bucket'] or not any([os.getenv('S3_INPUT_BUCKET'), os.getenv('S3_OUTPUT_BUCKET')]):
                st.code("# Single bucket with folders configuration")
                st.code("S3_BUCKET_NAME=your-bucket-name")
                st.code("S3_INPUT_FOLDER=inputfolder")
                st.code("S3_OUTPUT_FOLDER=outputfolder")
            else:
                st.code("# Separate buckets configuration")
                st.code("S3_INPUT_BUCKET=your-input-bucket")
                st.code("S3_OUTPUT_BUCKET=your-output-bucket")
            
            for var in missing_vars:
                if var not in ['S3_INPUT_BUCKET', 'S3_OUTPUT_BUCKET', 'S3_BUCKET_NAME']:
                    st.code(f"{var}=your_value_here")
            
            return None, None, None, None
        
        pdf_processor = PDFProcessor()
        bedrock_client = BedrockClient()
        output_handler = OutputHandler()
        bot_interface = BotInterface(bedrock_client=bedrock_client)
        
        return pdf_processor, bedrock_client, output_handler, bot_interface
    except Exception as e:
        st.error(f"Error initializing clients: {str(e)}")
        return None, None, None, None

# Initialize clients
pdf_processor, bedrock_client, output_handler, bot_interface = initialize_clients()

st.set_page_config(page_title="Financial PDF Extractor & Bot", layout="wide")

st.title("Financial Statement Extraction & Analysis")

st.markdown("""
This app allows you to select financial statement PDFs from an AWS S3 bucket, extract key financial attributes using AWS Bedrock Claude, and analyze the data with an interactive chatbot.

**S3 Configuration Support:**
- **Single Bucket Mode**: Use one bucket with separate folders for input and output
- **Separate Buckets Mode**: Use different buckets for input and output (legacy)
""")

# Check if clients are initialized
if not all([pdf_processor, bedrock_client, output_handler, bot_interface]):
    st.stop()

# Sidebar for S3 PDF selection
st.sidebar.header("Select PDFs from S3")

try:
    s3_config = get_s3_config()
    
    # Display S3 configuration
    st.sidebar.subheader("📁 S3 Configuration")
    if s3_config['use_single_bucket']:
        st.sidebar.success(f"**Bucket:** {s3_config['bucket_name']}")
        st.sidebar.info(f"**Input Folder:** {s3_config['input_folder']}")
        st.sidebar.info(f"**Output Folder:** {s3_config['output_folder']}")
    else:
        st.sidebar.info(f"**Input Bucket:** {s3_config['input_bucket']}")
        st.sidebar.info(f"**Output Bucket:** {s3_config['output_bucket']}")
    
    # List PDFs
    pdf_files = pdf_processor.list_pdfs_from_s3()
    
    if not pdf_files:
        st.sidebar.warning("No PDF files found in the S3 input location.")
        st.sidebar.info("Please upload PDF files to your configured input location.")
        st.stop()
    
    st.sidebar.success(f"Found {len(pdf_files)} PDF files")
    
    pdf_options = [f"{pdf['filename']} ({pdf['size_mb']} MB)" for pdf in pdf_files]
    selected_indices = st.sidebar.multiselect(
        "Select one or more PDFs to process", 
        range(len(pdf_options)), 
        format_func=lambda x: pdf_options[x]
    )
    
    selected_pdf_keys = [pdf_files[i]['key'] for i in selected_indices]
    selected_bucket = pdf_files[0]['bucket'] if pdf_files else None
    
except Exception as e:
    st.sidebar.error(f"Error accessing S3: {str(e)}")
    st.sidebar.info("Please check your AWS credentials and S3 configuration.")
    st.stop()

# Extract button
if st.sidebar.button("Extract Data from Selected PDFs"):
    if not selected_pdf_keys:
        st.sidebar.warning("Please select at least one PDF to extract.")
    else:
        with st.spinner("Processing PDFs and extracting data..."):
            # Process PDFs
            pdf_results = pdf_processor.process_multiple_pdfs(selected_bucket, selected_pdf_keys)
            
            # Extract attributes using Bedrock
            extracted_results = []
            for pdf_result in pdf_results:
                text = pdf_result.get('text', '')
                if not text:
                    pdf_result['extracted_attributes'] = {}
                    pdf_result['extraction_metadata'] = {
                        'processing_date': '',
                        'confidence_score': 0.0,
                        'extraction_method': pdf_result.get('extraction_method', 'none')
                    }
                    extracted_results.append(pdf_result)
                    continue
                
                attributes = bedrock_client.extract_attributes(text, config['attributes'])
                pdf_result['extracted_attributes'] = attributes.get('extracted_attributes', {})
                pdf_result['extraction_metadata'] = attributes.get('extraction_metadata', {})
                extracted_results.append(pdf_result)
            
            # Save outputs to S3
            output_summary = output_handler.process_and_save_all_outputs(extracted_results)
            
            # Update chatbot context
            bot_interface.set_context_data({"consolidated_data": extracted_results})
            
            st.success("Extraction and saving completed!")
            
            # Show download links
            st.header("Download Extracted Outputs")
            
            # Display S3 output location info
            if s3_config['use_single_bucket']:
                st.info(f"📁 Files saved to: **{s3_config['bucket_name']}/{s3_config['output_folder']}/**")
            else:
                st.info(f"📁 Files saved to: **{s3_config['output_bucket']}**")
            
            if output_summary.get("download_links"):
                dl_links = output_summary["download_links"]
                
                st.subheader("Individual JSON Files")
                for json_file in dl_links.get("individual_jsons", []):
                    confidence = json_file['confidence_score']
                    confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                    st.markdown(f"- {confidence_color} [{json_file['filename']}]({json_file['download_url']}) (Confidence: {confidence:.2%})")
                
                st.subheader("Consolidated Excel Report")
                excel_link = dl_links.get("consolidated_excel")
                if excel_link:
                    st.markdown(f"- 📊 [{excel_link['filename']}]({excel_link['download_url']}) - **Includes detailed confidence analysis**")
                else:
                    st.info("No consolidated Excel report available.")
                
                # Display confidence score explanation
                with st.expander("📊 Understanding Confidence Scores"):
                    st.markdown("""
                    **Confidence Score Calculation:**
                    
                    Each extracted attribute receives a confidence score (0-100%) based on four factors:
                    
                    1. **Text Clarity (25% weight)**: How clear and readable is the source text?
                       - 🟢 90-100%: Perfect, clear text with no ambiguity
                       - 🟡 60-89%: Minor formatting issues or slight ambiguity  
                       - 🔴 0-59%: Significant text quality issues or OCR errors
                    
                    2. **Exact Match (30% weight)**: How well does the found text match the attribute description?
                       - 🟢 90-100%: Perfect match with expected attribute name/label
                       - 🟡 60-89%: Close match with minor variations in terminology
                       - 🔴 0-59%: Weak match, significant interpretation needed
                    
                    3. **Context Match (25% weight)**: Is the value found in the right context/section?
                       - 🟢 90-100%: Found in perfect context (e.g., income statement for revenue)
                       - 🟡 60-89%: Found in appropriate section with minor context issues
                       - 🔴 0-59%: Found in questionable or wrong context
                    
                    4. **Format Validity (20% weight)**: Is the extracted value in the expected format?
                       - 🟢 90-100%: Perfect format (e.g., proper number format for currency)
                       - 🟡 60-89%: Minor format issues but clearly interpretable
                       - 🔴 0-59%: Significant format problems or invalid format
                    
                    **Final Formula:**
                    ```
                    Confidence = (Text Clarity × 0.25) + (Exact Match × 0.30) + (Context Match × 0.25) + (Format Validity × 0.20)
                    ```
                    
                    **Quality Indicators:**
                    - 🟢 **High Quality (80-100%)**: Reliable extraction, minimal review needed
                    - 🟡 **Medium Quality (50-79%)**: Good extraction, may need verification
                    - 🔴 **Low Quality (0-49%)**: Requires manual review and validation
                    """)
            else:
                st.info("No download links available.")
else:
    st.info("Select PDFs from the sidebar and click 'Extract Data from Selected PDFs' to begin.")

# Chatbot interface
st.header("Financial Data Chatbot")

user_question = st.text_input("Ask a question or provide an observation about the extracted financial data:")

if user_question:
    with st.spinner("Generating response..."):
        response = bot_interface.handle_user_input(user_question)
        st.markdown(f"**Bot:** {response.get('response', 'No response generated.')}")

# Environment status in sidebar
with st.sidebar:
    st.divider()
    st.subheader("Environment Status")
    
    # AWS Status
    aws_status = {
        "AWS Region": os.getenv('AWS_REGION', '❌ Not Set'),
        "AWS Access Key": "✅ Set" if os.getenv('AWS_ACCESS_KEY_ID') else "❌ Not Set",
        "AWS Secret Key": "✅ Set" if os.getenv('AWS_SECRET_ACCESS_KEY') else "❌ Not Set"
    }
    
    # S3 Status
    s3_config = get_s3_config()
    if s3_config['use_single_bucket']:
        aws_status.update({
            "S3 Bucket": s3_config['bucket_name'] or '❌ Not Set',
            "Input Folder": s3_config['input_folder'] or '❌ Not Set',
            "Output Folder": s3_config['output_folder'] or '❌ Not Set'
        })
    else:
        aws_status.update({
            "Input Bucket": s3_config['input_bucket'] or '❌ Not Set',
            "Output Bucket": s3_config['output_bucket'] or '❌ Not Set'
        })
    
    for key, value in aws_status.items():
        if "❌" in str(value):
            st.error(f"**{key}:** {value}")
        else:
            st.success(f"**{key}:** {value}")
