"""
Environment configuration module to ensure proper loading of environment variables
"""
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env file and validate required variables"""
    # Load from .env file
    load_dotenv()
    
    # Set default values if not provided
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = 'us-east-1'
        logger.info("AWS_REGION not found in environment, using default: us-east-1")
    
    if not os.getenv('BEDROCK_MODEL_ID'):
        os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-3-sonnet-20240229-v1:0'
        logger.info("BEDROCK_MODEL_ID not found in environment, using default model")
    
    # Log current environment variables (for debugging)
    logger.info(f"AWS_REGION: {os.getenv('AWS_REGION')}")
    logger.info(f"AWS_ACCESS_KEY_ID: {'Set' if os.getenv('AWS_ACCESS_KEY_ID') else 'Not Set'}")
    logger.info(f"AWS_SECRET_ACCESS_KEY: {'Set' if os.getenv('AWS_SECRET_ACCESS_KEY') else 'Not Set'}")
    logger.info(f"S3_INPUT_BUCKET: {os.getenv('S3_INPUT_BUCKET', 'Not Set')}")
    logger.info(f"S3_OUTPUT_BUCKET: {os.getenv('S3_OUTPUT_BUCKET', 'Not Set')}")
    
    return {
        'aws_region': os.getenv('AWS_REGION'),
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'aws_session_token': os.getenv('AWS_SESSION_TOKEN'),
        's3_input_bucket': os.getenv('S3_INPUT_BUCKET'),
        's3_output_bucket': os.getenv('S3_OUTPUT_BUCKET'),
        'bedrock_model_id': os.getenv('BEDROCK_MODEL_ID')
    }

def get_aws_session():
    """Create and return a properly configured AWS session"""
    env_vars = load_environment()
    
    try:
        import boto3
        session = boto3.Session(
            aws_access_key_id=env_vars['aws_access_key_id'],
            aws_secret_access_key=env_vars['aws_secret_access_key'],
            aws_session_token=env_vars['aws_session_token'],
            region_name=env_vars['aws_region']
        )
        logger.info(f"AWS session created successfully for region: {env_vars['aws_region']}")
        return session
    except Exception as e:
        logger.error(f"Failed to create AWS session: {str(e)}")
        raise

# Initialize environment on import
load_environment()
