#!/usr/bin/env python3
"""
Script to run the full catalog load function with VPC OpenSearch support
"""
import asyncio
import sys
import os
import logging
import argparse
import boto3
from botocore.exceptions import ClientError

# Add the current directory to the path so we can import from strands modules
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from utils.catalog_loader import catalog_loader

async def check_vpc_connectivity():
    """Check if we can connect to VPC-based OpenSearch and provide guidance"""
    print("🔍 Checking VPC connectivity for OpenSearch...")
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        # Check if OpenSearch endpoint is VPC-based
        opensearch_endpoint = settings.OPENSEARCH_ENDPOINT
        if not opensearch_endpoint:
            print("   ❌ OpenSearch endpoint not configured")
            return False
            
        # VPC endpoints typically have 'vpc-' prefix in their domain name
        is_vpc_endpoint = 'vpc-' in opensearch_endpoint
        
        if is_vpc_endpoint:
            print(f"   🔍 Detected VPC-based OpenSearch endpoint: {opensearch_endpoint}")
            print("   ℹ️  VPC OpenSearch requires network connectivity from within the VPC")
            
            # Check if we're running in an environment with VPC access
            vpc_access = await check_vpc_access()
            
            if not vpc_access:
                print("\n   ⚠️  WARNING: VPC OpenSearch detected but no VPC access available")
                print("   💡 To run this script with VPC OpenSearch, you have several options:")
                print("      1. Run from an EC2 instance within the same VPC")
                print("      2. Run from ECS Fargate task within the VPC (recommended)")
                print("      3. Use AWS Systems Manager Session Manager to connect to VPC")
                print("      4. Set up VPN connection to the VPC")
                print("      5. Use AWS Cloud9 environment within the VPC")
                print("\n   🚀 RECOMMENDED: Use ECS Fargate to run this script:")
                print("      - The AI service is already configured to run in the VPC")
                print("      - You can create a one-time ECS task to run this script")
                print("      - This ensures proper network connectivity to OpenSearch")
                
                return False
            else:
                print("   ✅ VPC access detected - should be able to connect to OpenSearch")
                return True
        else:
            print(f"   ✅ Public OpenSearch endpoint detected: {opensearch_endpoint}")
            return True
            
    except Exception as e:
        print(f"   ❌ VPC connectivity check failed: {str(e)}")
        return False

async def check_vpc_access():
    """Check if we have VPC access by testing AWS metadata service and network connectivity"""
    try:
        # Try to access EC2 metadata service (available in EC2/ECS/Fargate)
        import urllib.request
        import socket
        
        # Check if we're in AWS environment
        try:
            # This will work in EC2, ECS, Fargate
            req = urllib.request.Request('http://169.254.169.254/latest/meta-data/instance-id')
            req.add_header('X-aws-ec2-metadata-token-ttl-seconds', '21600')
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print("   ✅ Running in AWS environment (EC2/ECS/Fargate)")
                    return True
        except:
            pass
            
        # Check if we can resolve VPC DNS (another indicator)
        try:
            # Try to resolve a VPC endpoint pattern
            socket.gethostbyname('vpc-test.us-east-1.es.amazonaws.com')
            return True
        except:
            pass
            
        # Check environment variables that indicate VPC execution
        vpc_indicators = [
            'AWS_EXECUTION_ENV',  # Set in Lambda/Fargate
            'ECS_CONTAINER_METADATA_URI',  # Set in ECS
            'AWS_LAMBDA_FUNCTION_NAME'  # Set in Lambda
        ]
        
        for indicator in vpc_indicators:
            if os.getenv(indicator):
                print(f"   ✅ AWS execution environment detected: {indicator}")
                return True
                
        return False
        
    except Exception as e:
        print(f"   ⚠️  Could not determine VPC access: {str(e)}")
        return False

async def create_ecs_task_guidance():
    """Provide guidance on creating an ECS task to run this script"""
    print("\n" + "=" * 80)
    print("🚀 RUNNING IN VPC WITH ECS FARGATE")
    print("=" * 80)
    print("\nTo run this script with VPC OpenSearch access, create an ECS task:")
    print("\n1. Create a task definition:")
    print("   - Use the same image as the AI service")
    print("   - Override the command to run this script")
    print("   - Use the same VPC configuration")
    print("   - Use the same IAM role with OpenSearch permissions")
    
    print("\n2. Example AWS CLI command:")
    print("   aws ecs run-task \\")
    print("     --cluster <your-cluster-name> \\")
    print("     --task-definition <ai-service-task-def> \\")
    print("     --launch-type FARGATE \\")
    print("     --network-configuration 'awsvpcConfiguration={subnets=[<subnet-ids>],securityGroups=[<sg-ids>],assignPublicIp=ENABLED}' \\")
    print("     --overrides '{\"containerOverrides\":[{\"name\":\"<container-name>\",\"command\":[\"python\",\"run_catalog_load.py\",\"--auto-confirm\"]}]}'")
    
    print("\n3. Or use the AWS Console:")
    print("   - Go to ECS > Clusters > <your-cluster>")
    print("   - Click 'Run new task'")
    print("   - Select Fargate launch type")
    print("   - Choose the AI service task definition")
    print("   - Override the command to run this script")
    
    print("\n4. Monitor the task logs in CloudWatch")
    print("=" * 80)

async def run_full_data_load(load_products: bool = True, load_customers: bool = True):
    """Run the full data load process"""
    load_type = []
    if load_products:
        load_type.append("PRODUCTS")
    if load_customers:
        load_type.append("CUSTOMERS")
    
    print("=" * 80)
    print(f"STARTING FULL DATA LOAD: {' + '.join(load_type)}")
    print("=" * 80)
    
    try:
        print("\n🚀 Starting full data load process...")
        
        operations = []
        if load_products:
            operations.extend([
                "  1. Load product catalog from JSON file",
                "  2. Process products and generate embeddings", 
                "  3. Load products to DynamoDB",
                "  4. Create OpenSearch index and load products"
            ])
        if load_customers:
            operations.extend([
                f"  {len(operations) + 1}. Load customer profiles from JSON file",
                f"  {len(operations) + 2}. Load customers to DynamoDB"
            ])
        
        print("This will:")
        for operation in operations:
            print(operation)
        print()
        
        # Run the full data load
        result = await catalog_loader.full_data_load(load_products=load_products, load_customers=load_customers)
        
        print("\n" + "=" * 80)
        print("✅ DATA LOAD COMPLETED!")
        print("=" * 80)
        
        # Display results
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   Overall Success: {result.get('success', False)}")
        if result.get('errors'):
            print(f"   Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"     - {error}")
        
        # Product results
        if load_products and 'product_result' in result:
            product_result = result['product_result']
            print(f"\n📦 Product Results:")
            print(f"   Total Products: {product_result.get('total_products', 0)}")
            print(f"   Products Loaded: {result.get('products_loaded', False)}")
            
            # DynamoDB results
            dynamodb_result = product_result.get('dynamodb_result', {})
            print(f"\n📦 Product DynamoDB Results:")
            print(f"   Products Written: {dynamodb_result.get('products_written', 0)}")
            print(f"   Success: {dynamodb_result.get('success', False)}")
            
            # OpenSearch results
            opensearch_result = product_result.get('opensearch_result', {})
            print(f"\n🔍 OpenSearch Results:")
            print(f"   Products Indexed: {opensearch_result.get('successful', 0)}")
            print(f"   Failed: {opensearch_result.get('failed', 0)}")
            print(f"   Success: {opensearch_result.get('success', False)}")
            
            # Catalog info
            catalog_info = product_result.get('catalog_info', {})
            if catalog_info:
                print(f"\n📋 Catalog Info:")
                for key, value in catalog_info.items():
                    print(f"   {key}: {value}")

        # Customer results
        if load_customers and 'customer_result' in result:
            customer_result = result['customer_result']
            print(f"\n👥 Customer Results:")
            print(f"   Total Customers: {customer_result.get('total_customers', 0)}")
            print(f"   Customers Loaded: {result.get('customers_loaded', False)}")
            
            # DynamoDB results
            customer_dynamodb_result = customer_result.get('dynamodb_result', {})
            print(f"\n📦 Customer DynamoDB Results:")
            print(f"   Customers Written: {customer_dynamodb_result.get('customers_written', 0)}")
            print(f"   Customers Failed: {customer_dynamodb_result.get('customers_failed', 0)}")
            print(f"   Success: {customer_dynamodb_result.get('success', False)}")
            
            # Profile info
            profile_info = customer_result.get('profile_info', {})
            if profile_info:
                print(f"\n📋 Customer Profile Info:")
                for key, value in profile_info.items():
                    print(f"   {key}: {value}")
        
        print(f"\n✅ Full data load completed!")
        return True
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: Catalog file not found")
        print(f"   {str(e)}")
        print(f"\n💡 Make sure the product_catalog.json file exists in:")
        print(f"   - ./data/product_catalog.json")
        print(f"   - ../data/product_catalog.json")
        print(f"   - data/product_catalog.json")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: Catalog load failed")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        
        # Print more detailed error info if available
        import traceback
        print(f"\n🔍 Detailed Error Trace:")
        traceback.print_exc()
        return False

async def check_prerequisites(skip_opensearch_health: bool = False):
    """Check if all prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    # Check if catalog file exists
    from pathlib import Path
    possible_paths = [
        Path("./data/product_catalog.json"),
        Path("../data/product_catalog.json"),
        Path("data/product_catalog.json"),
    ]
    
    catalog_found = False
    for path in possible_paths:
        if path.exists():
            print(f"   ✅ Found catalog file: {path}")
            catalog_found = True
            break
    
    if not catalog_found:
        print(f"   ❌ Catalog file not found in any of these locations:")
        for path in possible_paths:
            print(f"      - {path}")
        return False
    
    # Check services
    try:
        from services.opensearch_service import opensearch_service
        from services.bedrock_service import bedrock_service
        from services.dynamodb_service import dynamodb_service
        
        print("   ✅ All required services imported successfully")
        
        # Check OpenSearch health with timeout
        if not skip_opensearch_health:
            try:
                print("   🔍 Checking OpenSearch connectivity...")
                health = await asyncio.wait_for(opensearch_service.health_check(), timeout=10.0)
                if health.get('status') == 'healthy':
                    print("   ✅ OpenSearch service is healthy")
                else:
                    print(f"   ⚠️  OpenSearch service status: {health.get('status')}")
                    print(f"      Message: {health.get('message')}")
                    print("   ℹ️  Note: Data load will attempt to connect during execution")
            except asyncio.TimeoutError:
                print("   ⚠️  OpenSearch health check timed out")
                print("   ℹ️  Note: Data load will attempt to connect during execution")
            except Exception as e:
                print(f"   ⚠️  OpenSearch health check failed: {str(e)}")
                print("   ℹ️  Note: Data load will attempt to connect during execution")
        else:
            print("   ⏭️  Skipping OpenSearch health check")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Service check failed: {str(e)}")
        return False

def get_user_input(prompt: str, default: str = "", non_interactive: bool = False) -> str:
    """Get user input with support for non-interactive mode"""
    if non_interactive:
        print(f"{prompt} [Non-interactive mode: using default '{default}']")
        return default
    else:
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            return "cancel"

async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Product Data Loader')
    parser.add_argument('--non-interactive', '-n', action='store_true', 
                       help='Run in non-interactive mode with defaults')
    parser.add_argument('--products-only', action='store_true',
                       help='Load products only')
    parser.add_argument('--customers-only', action='store_true',
                       help='Load customers only')
    parser.add_argument('--skip-opensearch-health', action='store_true',
                       help='Skip OpenSearch health check (faster startup)')
    parser.add_argument('--auto-confirm', '-y', action='store_true',
                       help='Automatically confirm all prompts')
    
    args = parser.parse_args()
    
    print("📦 Product Data Loader")
    print("=" * 80)
    
    # Check VPC connectivity first
    vpc_ok = await check_vpc_connectivity()
    if not vpc_ok:
        print("\n❌ VPC connectivity check failed.")
        await create_ecs_task_guidance()
        return False
    
    # Check prerequisites
    prereqs_ok = await check_prerequisites(skip_opensearch_health=args.skip_opensearch_health)
    if not prereqs_ok:
        print("\n❌ Prerequisites check failed. Please fix the issues above.")
        return False
    
    print("\n✅ All checks passed!")

    # Determine what to load
    if args.products_only and args.customers_only:
        print("❌ Cannot specify both --products-only and --customers-only")
        return False
    
    if args.products_only:
        load_products = True
        load_customers = False
        print("\n📋 Loading: Products only (from --products-only flag)")
    elif args.customers_only:
        load_products = False
        load_customers = True
        print("\n📋 Loading: Customers only (from --customers-only flag)")
    else:
        load_products = True
        load_customers = True
        print("\n📋 Loading: Both products and customers (default)")
    
    # Run the data load
    success = await run_full_data_load(load_products=load_products, load_customers=load_customers)
    
    if success:
        success_messages = []
        if load_products:
            success_messages.extend([
                "   - Products are indexed in OpenSearch for semantic and keyword search",
                "   - Products are stored in DynamoDB for fast retrieval", 
                "   - Embeddings are generated for semantic search capabilities"
            ])
        if load_customers:
            success_messages.extend([
                "   - Customer profiles are stored in DynamoDB",
                "   - Customer data is ready for personalized recommendations"
            ])
            
        print(f"\n🎉 All done! Your data is now loaded and ready!")
        for msg in success_messages:
            print(msg)
    
    return success

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
