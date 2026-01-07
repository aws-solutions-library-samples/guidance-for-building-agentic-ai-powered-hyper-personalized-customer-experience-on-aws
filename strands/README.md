# CX VHS - Product Catalog API

A simplified AI-powered product search and customer management platform built with FastAPI, AWS services, and modern Python practices.

## Features

- **Product Search**: Keyword and semantic search capabilities
- **Customer Management**: Create and manage customer profiles
- **AI-Powered Recommendations**: Personalized product suggestions using Amazon Bedrock
- **Real-time Chat**: WebSocket-based product search assistance
- **Health Checks**: Comprehensive service monitoring

## Technology Stack

- **Backend**: FastAPI 0.115.6, Python 3.8+
- **Database**: Amazon DynamoDB
- **Search**: Amazon OpenSearch Serverless
- **AI/ML**: Amazon Bedrock (Titan Embeddings, Claude)
- **Authentication**: AWS IAM
- **Deployment**: Docker, AWS

## Quick Start

### Prerequisites

1. Python 3.8 or higher
2. AWS Account with appropriate permissions
3. AWS CLI configured

### Installation

1. Clone the repository and navigate to the strands folder:
```bash
cd strands
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up AWS resources (see [AWS Resources Guide](infrastructure/aws_resources.md))

4. Create environment variables:
```bash
cp .env.example .env
# Edit .env with your AWS configuration
```

5. Run the application:
```bash
python app.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

## Key Endpoints

### Health & Status
- `GET /health` - Service health check

### Catalog Management
- `POST /catalog/upload` - Upload product catalog
- `POST /catalog/load-sample` - Load sample product catalog

### Search
- `POST /search/keyword` - Keyword-based product search
- `POST /search/semantic` - AI-powered semantic search
- `POST /search/personalized` - Personalized recommendations

### Customer Management
- `POST /customers` - Create customer
- `GET /customers/{customer_id}` - Get customer details

### Real-time Features
- `WebSocket /ws/chat/{user_id}` - Real-time chat for product assistance

## Project Structure

```
strands/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── config/
│   └── settings.py       # Application configuration
├── models/
│   └── schemas.py        # Pydantic data models
├── services/
│   ├── dynamodb_service.py    # DynamoDB operations
│   ├── opensearch_service.py  # OpenSearch operations
│   └── bedrock_service.py     # Bedrock AI operations
├── utils/
│   ├── catalog_loader.py      # Product catalog utilities
│   └── websocket_utils.py     # WebSocket connection management
└── infrastructure/
    └── aws_resources.md       # AWS setup guide
```

## Configuration

Key environment variables:

```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# DynamoDB Tables
DYNAMODB_CUSTOMERS_TABLE=customers
DYNAMODB_PRODUCTS_TABLE=products
DYNAMODB_SEARCH_HISTORY_TABLE=search_history

# OpenSearch
OPENSEARCH_ENDPOINT=https://your-collection.aoss.amazonaws.com
OPENSEARCH_INDEX_NAME=products-catalog

# Bedrock
BEDROCK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0

# Application
DEBUG=true
PORT=8000
CORS_ORIGINS=http://localhost:3000
```

## AWS Resources Required

See the detailed [AWS Resources Guide](infrastructure/aws_resources.md) for:
- DynamoDB table setup
- OpenSearch Serverless collection configuration
- Bedrock model access
- IAM permissions
- Cost estimates

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

### Docker
```bash
# Build image
docker build -t cx-vhs-api .

# Run container
docker run -p 8000:8000 --env-file .env cx-vhs-api
```

## Sample Usage

### Load Sample Catalog
```bash
curl -X POST "http://localhost:8000/catalog/load-sample"
```

### Search Products
```bash
curl -X POST "http://localhost:8000/search/keyword" \
  -H "Content-Type: application/json" \
  -d '{"query": "vitamin D supplements", "size": 5}'
```

### Create Customer
```bash
curl -X POST "http://localhost:8000/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "age": 35,
    "health_goals": ["immune support", "energy boost"]
  }'
```

## Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure AWS credentials are properly configured
2. **Service Health**: Check `/health` endpoint for service status
3. **Model Access**: Verify Bedrock model access in AWS console
4. **Network**: Ensure OpenSearch collection has proper network policies

### Debug Mode
Set `DEBUG=true` in environment variables for detailed logging.

## Contributing

1. Follow PEP 8 style guidelines
2. Add tests for new features
3. Update documentation
4. Ensure all services pass health checks

## License

This project is part of the CX VHS platform POC.
