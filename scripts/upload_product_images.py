#!/usr/bin/env python3
"""
Product Image Uploader Script

This script uploads product images from a local directory to an S3 bucket
for use with the healthcare product catalog.

Usage:
    python upload_product_images.py --images-dir /path/to/images --bucket-name your-bucket-name

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 library installed (pip install boto3)
    - Images named according to product IDs (e.g., VIT001.png, SKIN001.jpg, etc.)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import mimetypes

class ProductImageUploader:
    def __init__(self, bucket_name: str, aws_profile: str = None):
        """Initialize the uploader with S3 client."""
        try:
            if aws_profile:
                session = boto3.Session(profile_name=aws_profile)
                self.s3_client = session.client('s3')
            else:
                self.s3_client = boto3.client('s3')
            
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            self.bucket_name = bucket_name
            print(f"✅ Successfully connected to S3 bucket: {bucket_name}")
            
        except NoCredentialsError:
            print("❌ Error: AWS credentials not found. Please configure AWS CLI or set environment variables.")
            sys.exit(1)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Error: S3 bucket '{bucket_name}' not found.")
            elif error_code == '403':
                print(f"❌ Error: Access denied to S3 bucket '{bucket_name}'. Check your permissions.")
            else:
                print(f"❌ Error accessing S3 bucket: {e}")
            sys.exit(1)

    def load_product_catalog(self, catalog_path: str) -> Set[str]:
        """Load product IDs from the catalog file."""
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            product_ids = set()
            for product in catalog.get('products', []):
                product_ids.add(product['id'])
            
            print(f"📋 Loaded {len(product_ids)} product IDs from catalog")
            return product_ids
            
        except FileNotFoundError:
            print(f"❌ Error: Catalog file not found: {catalog_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON in catalog file: {catalog_path}")
            sys.exit(1)

    def find_image_files(self, images_dir: str, product_ids: Set[str]) -> Dict[str, str]:
        """Find image files that match product IDs."""
        images_path = Path(images_dir)
        if not images_path.exists():
            print(f"❌ Error: Images directory not found: {images_dir}")
            sys.exit(1)

        # Common image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        
        found_images = {}
        missing_products = set(product_ids)
        
        # Search for image files
        for file_path in images_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Extract product ID from filename (remove extension)
                product_id = file_path.stem.upper()
                
                if product_id in product_ids:
                    found_images[product_id] = str(file_path)
                    missing_products.discard(product_id)
                    print(f"📸 Found image for {product_id}: {file_path.name}")
        
        print(f"\n📊 Summary:")
        print(f"   Found images: {len(found_images)}")
        print(f"   Missing images: {len(missing_products)}")
        
        if missing_products:
            print(f"\n⚠️  Missing images for products: {', '.join(sorted(missing_products))}")
        
        return found_images

    def upload_image(self, product_id: str, local_path: str, dry_run: bool = False) -> bool:
        """Upload a single image to S3."""
        try:
            # Determine content type
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # S3 key (path in bucket)
            file_extension = Path(local_path).suffix.lower()
            s3_key = f"images/{product_id}{file_extension}"
            
            if dry_run:
                print(f"🔍 [DRY RUN] Would upload {local_path} -> s3://{self.bucket_name}/{s3_key}")
                return True
            
            # Upload file
            with open(local_path, 'rb') as f:
                self.s3_client.upload_fileobj(
                    f, 
                    self.bucket_name, 
                    s3_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'CacheControl': 'max-age=31536000'  # 1 year cache
                        # Note: Public access is handled by bucket policy, not ACLs
                    }
                )
            
            print(f"✅ Uploaded {product_id}: {local_path} -> s3://{self.bucket_name}/{s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to upload {product_id}: {e}")
            return False

    def upload_all_images(self, image_files: Dict[str, str], dry_run: bool = False) -> None:
        """Upload all found images to S3."""
        if not image_files:
            print("❌ No images to upload.")
            return
        
        if dry_run:
            print(f"\n🔍 DRY RUN MODE - No files will actually be uploaded")
        
        print(f"\n🚀 Starting upload of {len(image_files)} images...")
        
        successful_uploads = 0
        failed_uploads = 0
        
        for product_id, local_path in image_files.items():
            if self.upload_image(product_id, local_path, dry_run):
                successful_uploads += 1
            else:
                failed_uploads += 1
        
        print(f"\n📊 Upload Summary:")
        print(f"   Successful: {successful_uploads}")
        print(f"   Failed: {failed_uploads}")
        
        if not dry_run and successful_uploads > 0:
            print(f"\n🎉 Images are now available via CloudFront at:")
            print(f"   https://your-cloudfront-domain.cloudfront.net/images/{{PRODUCT_ID}}.{{ext}}")

def main():
    parser = argparse.ArgumentParser(description='Upload product images to S3 bucket')
    parser.add_argument('--images-dir', required=True, help='Directory containing product images')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name')
    parser.add_argument('--catalog-path', default='../strands/data/healthcare_product_catalog.json', 
                       help='Path to product catalog JSON file')
    parser.add_argument('--aws-profile', help='AWS profile to use (optional)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be uploaded without actually uploading')
    
    args = parser.parse_args()
    
    print("🏥 Healthcare Product Image Uploader")
    print("=" * 40)
    
    # Initialize uploader
    uploader = ProductImageUploader(args.bucket_name, args.aws_profile)
    
    # Load product catalog
    product_ids = uploader.load_product_catalog(args.catalog_path)
    
    # Find matching image files
    image_files = uploader.find_image_files(args.images_dir, product_ids)
    
    if not image_files:
        print("\n❌ No matching image files found. Please check:")
        print("   1. Image files are named with product IDs (e.g., VIT001.png)")
        print("   2. Image files have supported extensions (.jpg, .jpeg, .png, .gif, .webp, .bmp)")
        print("   3. Images directory path is correct")
        sys.exit(1)
    
    # Confirm upload
    if not args.dry_run:
        response = input(f"\n❓ Upload {len(image_files)} images to s3://{args.bucket_name}/images/? (y/N): ")
        if response.lower() != 'y':
            print("❌ Upload cancelled.")
            sys.exit(0)
    
    # Upload images
    uploader.upload_all_images(image_files, args.dry_run)

if __name__ == '__main__':
    main()
