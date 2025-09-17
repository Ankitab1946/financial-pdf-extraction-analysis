# S3 Bucket Configuration Guide

## Overview

The Financial PDF Extraction system supports two S3 configuration modes to accommodate different organizational setups and security requirements.

## Configuration Modes

### 1. Single Bucket with Folders (Recommended)

This mode uses a single S3 bucket with separate folders for input and output files.

**Structure:**
```
your-bucket-name/
├── inputfolder/
│   ├── Q1_2023_Financial_Statement.pdf
│   ├── Q2_2023_Financial_Statement.pdf
│   └── Annual_Report_2023.pdf
└── outputfolder/
    ├── individual_jsons/
    │   ├── Q1_2023_Financial_Statement_20240117_143022.json
    │   └── Q2_2023_Financial_Statement_20240117_143045.json
    └── consolidated_reports/
        └── consolidated_financial_report_20240117_143100.xlsx
```

**Environment Variables:**
```bash
# Single bucket configuration
S3_BUCKET_NAME=your-bucket-name
S3_INPUT_FOLDER=inputfolder
S3_OUTPUT_FOLDER=outputfolder
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

**Benefits:**
- ✅ Simplified bucket management
- ✅ Easier IAM permissions setup
- ✅ Cost-effective (single bucket)
- ✅ Clear organization with folders
- ✅ Reduced configuration complexity

### 2. Separate Buckets (Legacy)

This mode uses separate S3 buckets for input and output files.

**Structure:**
```
input-bucket/
├── Q1_2023_Financial_Statement.pdf
├── Q2_2023_Financial_Statement.pdf
└── Annual_Report_2023.pdf

output-bucket/
├── Output/
│   ├── individual_jsons/
│   │   ├── Q1_2023_Financial_Statement_20240117_143022.json
│   │   └── Q2_2023_Financial_Statement_20240117_143045.json
│   └── consolidated_reports/
│       └── consolidated_financial_report_20240117_143100.xlsx
```

**Environment Variables:**
```bash
# Separate buckets configuration
S3_INPUT_BUCKET=your-input-bucket-name
S3_OUTPUT_BUCKET=your-output-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Setup Instructions

### Step 1: Choose Configuration Mode

**For Single Bucket (Recommended):**
1. Create one S3 bucket (e.g., `financial-data-processing`)
2. Create two folders: `inputfolder` and `outputfolder`
3. Set environment variables for single bucket mode

**For Separate Buckets:**
1. Create two S3 buckets (e.g., `financial-input` and `financial-output`)
2. Set environment variables for separate bucket mode

### Step 2: Configure Environment Variables

Create a `.env` file in your project root:

**Single Bucket Configuration:**
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=abc123...
AWS_SESSION_TOKEN=IQoJb3JpZ2luX2VjE...  # Optional for temporary credentials
AWS_REGION=us-east-1

# S3 Single Bucket Configuration
S3_BUCKET_NAME=financial-data-processing
S3_INPUT_FOLDER=inputfolder
S3_OUTPUT_FOLDER=outputfolder

# Optional: Bedrock Model Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

**Separate Buckets Configuration:**
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=abc123...
AWS_SESSION_TOKEN=IQoJb3JpZ2luX2VjE...  # Optional for temporary credentials
AWS_REGION=us-east-1

# S3 Separate Buckets Configuration
S3_INPUT_BUCKET=financial-input-bucket
S3_OUTPUT_BUCKET=financial-output-bucket

# Optional: Bedrock Model Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### Step 3: Set Up IAM Permissions

**For Single Bucket Mode:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/inputfolder/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name/outputfolder/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
            ]
        }
    ]
}
```

**For Separate Buckets Mode:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-input-bucket",
                "arn:aws:s3:::your-input-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-output-bucket",
                "arn:aws:s3:::your-output-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
            ]
        }
    ]
}
```

## File Organization

### Input Files
- **Location**: `{bucket}/{input_folder}/` or `{input_bucket}/`
- **Format**: PDF files only
- **Naming**: Any valid filename (e.g., `Q1_2023_Statement.pdf`)
- **Size Limit**: 100MB per file

### Output Files

#### Individual JSON Files
- **Location**: `{bucket}/{output_folder}/individual_jsons/` or `{output_bucket}/Output/individual_jsons/`
- **Format**: JSON with extraction results and confidence scores
- **Naming**: `{original_filename}_{timestamp}.json`

#### Consolidated Excel Reports
- **Location**: `{bucket}/{output_folder}/consolidated_reports/` or `{output_bucket}/Output/consolidated_reports/`
- **Format**: Multi-sheet Excel workbook
- **Naming**: `consolidated_financial_report_{timestamp}.xlsx`

## Application Behavior

### Automatic Detection
The application automatically detects which configuration mode to use:

1. **Checks for `S3_BUCKET_NAME`** - If present, uses single bucket mode
2. **Falls back to separate buckets** - If `S3_INPUT_BUCKET` and `S3_OUTPUT_BUCKET` are present
3. **Shows configuration error** - If neither configuration is complete

### UI Indicators
The application displays the current S3 configuration in the sidebar:

**Single Bucket Mode:**
```
📁 S3 Configuration
✅ Bucket: financial-data-processing
📂 Input Folder: inputfolder
📂 Output Folder: outputfolder
```

**Separate Buckets Mode:**
```
📁 S3 Configuration
📁 Input Bucket: financial-input-bucket
📁 Output Bucket: financial-output-bucket
```

## Migration Guide

### From Separate Buckets to Single Bucket

1. **Create new folder structure** in your existing bucket or create a new bucket
2. **Move existing PDFs** to the input folder
3. **Update environment variables** to use single bucket configuration
4. **Restart the application**

### From Single Bucket to Separate Buckets

1. **Create separate input and output buckets**
2. **Move PDFs** to the input bucket
3. **Update environment variables** to use separate bucket configuration
4. **Restart the application**

## Troubleshooting

### Common Issues

**"Missing required environment variables"**
- Ensure your `.env` file is in the project root directory
- Check that variable names match exactly (case-sensitive)
- Verify no extra spaces around the `=` sign

**"Error accessing S3"**
- Verify AWS credentials are correct and have necessary permissions
- Check that bucket names exist and are accessible
- Ensure the specified folders exist in single bucket mode

**"No PDF files found"**
- Verify PDFs are uploaded to the correct location
- Check folder names match your configuration
- Ensure files have `.pdf` extension

### Debug Information

The application logs detailed information about S3 configuration:
- Current bucket and folder settings
- Number of PDFs found
- File processing status
- Upload locations for outputs

Check the application logs for detailed debugging information.

## Best Practices

### Security
- Use IAM roles when running on AWS infrastructure
- Implement least-privilege access policies
- Enable S3 bucket encryption
- Use VPC endpoints for private network access

### Organization
- Use consistent naming conventions for folders
- Implement lifecycle policies for automatic cleanup
- Monitor storage costs and usage
- Regular backup of important outputs

### Performance
- Keep input files under 100MB for optimal processing
- Use appropriate AWS regions for your location
- Consider S3 Transfer Acceleration for large files
- Monitor Bedrock API usage and costs

This flexible S3 configuration system ensures the application can adapt to various organizational requirements while maintaining security and performance.
