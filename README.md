# Financial PDF Extraction & Analysis System

A comprehensive Python-based AI solution that extracts financial data from PDF statements using AWS Bedrock Claude, saves results to S3, and provides an intelligent chatbot for financial analysis.

## 🚀 Features

- **PDF Processing**: Extract data from both text-based and scanned image PDFs
- **AI-Powered Extraction**: Uses AWS Bedrock Claude for intelligent attribute extraction
- **S3 Integration**: Seamless integration with AWS S3 for input and output storage
- **Excel Reports**: Generates comprehensive consolidated Excel reports with multiple sheets
- **Interactive Chatbot**: AI-powered chatbot for financial data analysis and insights
- **Modern UI**: Clean Streamlit interface for easy interaction
- **Docker Support**: Fully containerized application
- **CI/CD Pipeline**: GitHub Actions workflow for automated testing and deployment
- **Large File Handling**: Optimized for processing large financial documents

## 📋 Requirements

### System Requirements
- Python 3.10+
- Docker (optional)
- Tesseract OCR for scanned PDF processing

### AWS Requirements
- AWS Account with Bedrock access
- S3 buckets for input and output
- IAM permissions for Bedrock and S3

## 🛠️ Installation

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd financial-pdf-extractor
   ```

2. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-eng

   # macOS
   brew install tesseract

   # Windows
   # Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and S3 bucket names
   ```

### Docker Setup

1. **Build the Docker image**
   ```bash
   docker build -t financial-pdf-extractor .
   ```

2. **Run with environment variables**
   ```bash
   docker run -p 8000:8000 \
     -e AWS_ACCESS_KEY_ID=your_access_key \
     -e AWS_SECRET_ACCESS_KEY=your_secret_key \
     -e AWS_SESSION_TOKEN=your_session_token \
     -e AWS_REGION=us-east-1 \
     -e S3_INPUT_BUCKET=your-input-bucket \
     -e S3_OUTPUT_BUCKET=your-output-bucket \
     financial-pdf-extractor
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key | Yes |
| `AWS_SESSION_TOKEN` | AWS Session Token (if using temporary credentials) | No |
| `AWS_REGION` | AWS Region (default: us-east-1) | Yes |
| `S3_INPUT_BUCKET` | S3 bucket name for input PDFs | Yes |
| `S3_OUTPUT_BUCKET` | S3 bucket name for output files | Yes |
| `BEDROCK_MODEL_ID` | Bedrock model ID (default: anthropic.claude-3-sonnet-20240229-v1:0) | No |

### Configuration File

Edit `config.yaml` to customize:
- Financial attributes to extract
- AWS Bedrock model settings
- Excel report formatting
- Chatbot behavior

## 🚀 Usage

### Starting the Application

1. **Local development**
   ```bash
   streamlit run app.py --server.port=8000
   ```

2. **Docker**
   ```bash
   docker run -p 8000:8000 financial-pdf-extractor
   ```

3. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

### Using the Application

1. **Upload PDFs**: Place your financial statement PDFs in the configured S3 input bucket

2. **Select PDFs**: Use the sidebar to select one or multiple PDFs for processing

3. **Extract Data**: Click the "Extract Financial Data" button to process selected PDFs

4. **Download Results**: 
   - Individual JSON files for each PDF
   - Consolidated Excel report with multiple analysis sheets

5. **Chat with Data**: Use the chatbot interface to ask questions about the extracted financial data

## 📊 Output Formats

### Individual JSON Files
Each processed PDF generates a JSON file containing:
- Extracted financial attributes
- Confidence scores
- Processing metadata
- Source text references

### Consolidated Excel Report
Multi-sheet Excel file with:
- **Summary Dashboard**: Overview statistics and key metrics
- **Consolidated Data**: All extracted data in tabular format
- **Year-over-Year Analysis**: Comparative analysis across years
- **Monthly Breakdown**: Quarterly/monthly data breakdown
- **Individual PDF Details**: Processing details per PDF
- **Data Quality Report**: Extraction confidence and quality metrics

## 🤖 Chatbot Features

The integrated chatbot can:
- Answer questions about specific financial metrics
- Provide insights on trends and patterns
- Explain financial ratios and their implications
- Compare data across different periods
- Identify potential areas of concern or opportunity

Example questions:
- "What is the total revenue across all periods?"
- "Show me the year-over-year growth in net income"
- "What are the key financial ratios?"
- "Compare the profitability trends"

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_pdf_processor.py -v
```

### Test Coverage

The test suite includes:
- PDF processing functionality
- AWS Bedrock integration
- Excel report generation
- Error handling scenarios
- Edge cases and validation

## 🔧 Development

### Project Structure

```
financial-pdf-extractor/
├── app.py                      # Main Streamlit application
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── .env.example               # Environment variables template
├── README.md                  # This file
├── bedrock_client.py          # AWS Bedrock integration
├── pdf_processor.py           # PDF processing logic
├── excel_generator.py         # Excel report generation
├── output_handler.py          # S3 output management
├── bot_interface.py           # Chatbot functionality
├── tests/                     # Test files
│   ├── test_pdf_processor.py
│   └── test_bedrock_client.py
└── .github/workflows/         # CI/CD pipeline
    └── ci.yml
```

### Adding New Features

1. **New Financial Attributes**: Edit `config.yaml` to add new attributes
2. **Custom Excel Sheets**: Modify `excel_generator.py`
3. **Enhanced Chatbot**: Update `bot_interface.py`
4. **Additional PDF Formats**: Extend `pdf_processor.py`

### Code Quality

The project uses:
- **Black**: Code formatting
- **Flake8**: Linting
- **isort**: Import sorting
- **Pytest**: Testing framework
- **GitHub Actions**: CI/CD pipeline

## 🚀 Deployment

### AWS ECS Deployment

1. **Push to ECR**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker tag financial-pdf-extractor:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/financial-pdf-extractor:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/financial-pdf-extractor:latest
   ```

2. **Create ECS Task Definition**
3. **Deploy to ECS Service**

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: financial-pdf-extractor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: financial-pdf-extractor
  template:
    metadata:
      labels:
        app: financial-pdf-extractor
    spec:
      containers:
      - name: app
        image: financial-pdf-extractor:latest
        ports:
        - containerPort: 8000
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: access-key-id
        # Add other environment variables
```

## 🔒 Security Considerations

- **AWS Credentials**: Use IAM roles when possible, avoid hardcoding credentials
- **S3 Bucket Policies**: Implement least-privilege access policies
- **Network Security**: Use VPC endpoints for AWS services
- **Data Encryption**: Enable S3 bucket encryption
- **Input Validation**: All user inputs are validated and sanitized

## 📈 Performance Optimization

- **Concurrent Processing**: Multiple PDFs processed in parallel
- **Streaming**: Large files are processed in chunks
- **Caching**: Streamlit caching for improved UI performance
- **Resource Management**: Proper cleanup of temporary files and connections

## 🐛 Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify environment variables are set correctly
   - Check IAM permissions for Bedrock and S3

2. **PDF Processing Fails**
   - Ensure Tesseract is installed for OCR
   - Check PDF file integrity

3. **S3 Access Denied**
   - Verify bucket names and permissions
   - Check bucket policies and CORS settings

4. **Bedrock Model Not Available**
   - Verify model access in your AWS region
   - Check Bedrock service availability

### Logs and Debugging

- Application logs are written to `app.log`
- Use `LOG_LEVEL=DEBUG` for detailed logging
- Check Docker container logs: `docker logs <container-id>`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section
- Review the configuration documentation

## 🔄 Changelog

### Version 1.0.0
- Initial release
- PDF processing with OCR support
- AWS Bedrock integration
- Excel report generation
- Interactive chatbot
- Docker support
- CI/CD pipeline

---

**Note**: This application requires AWS credentials and appropriate permissions for Bedrock and S3 services. Ensure you have the necessary access before deployment.
