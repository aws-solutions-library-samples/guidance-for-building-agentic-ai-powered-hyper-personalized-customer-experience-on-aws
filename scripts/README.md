# Product Image Upload Script

This script uploads product images from your local machine to the S3 bucket and makes them available via CloudFront for the healthcare product catalog.

## Prerequisites

1. **AWS Credentials**: Ensure you have AWS credentials configured with permissions to upload to S3
2. **Python 3.7+**: Required to run the upload script
3. **Product Images**: Image files named according to product IDs (e.g., `VIT001.png`, `SKIN001.png`)

## Setup

### 1. Install Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Choose one of the following methods:

#### Option A: AWS CLI (Recommended)
```bash
aws configure
```
Enter your AWS Access Key ID, Secret Access Key, and default region.

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: IAM Role (if running on EC2)
No additional configuration needed if your EC2 instance has an IAM role with S3 permissions.

### 3. Organize Your Image Files

Create a directory structure like this:
```
images/
├── VIT001.png
├── VIT002.png
├── SKIN001.png
├── SKIN002.png
├── OTC001.png
└── ...
```

**Important**: Image filenames must match the product IDs from the catalog (without file extension).

## Usage

### Basic Upload

```bash
python upload_product_images.py --bucket-name your-s3-bucket-name --images-dir /path/to/your/images
```

### Dry Run (Preview Only)

Test the script without actually uploading files:

```bash
python upload_product_images.py --bucket-name your-s3-bucket-name --images-dir /path/to/your/images --dry-run
```

### Custom Catalog File

If your catalog file is in a different location:

```bash
python upload_product_images.py --bucket-name your-s3-bucket-name --images-dir /path/to/your/images --catalog-file /path/to/catalog.json
```

## Command Line Options

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `--bucket-name` | S3 bucket name | Yes | - |
| `--images-dir` | Directory containing image files | Yes | - |
| `--catalog-file` | Path to product catalog JSON | No | `../strands/data/healthcare_product_catalog.json` |
| `--dry-run` | Preview actions without uploading | No | False |

## What the Script Does

1. **Loads Product Catalog**: Reads the healthcare product catalog to get all product IDs
2. **Discovers Images**: Scans your images directory for files matching product IDs
3. **Validates Files**: Checks that image files exist for products
4. **Uploads to S3**: Uploads images with proper metadata:
   - Sets correct Content-Type based on file extension
   - Adds Cache-Control headers for optimal performance
   - Makes files publicly readable
5. **Reports Results**: Shows upload progress and summary

## Image Requirements

- **Supported Formats**: PNG, JPG, JPEG, GIF, WebP, SVG
- **Naming Convention**: Must match product ID exactly (case-sensitive)
  - Example: Product ID `VIT001` → Image file `VIT001.png`
- **File Size**: Recommended under 5MB for optimal loading performance
- **Dimensions**: Recommended 800x800px or similar square aspect ratio

## Example Output

```
Starting product image upload...
Loaded 48 products from catalog
Found 45 matching image files

Uploading images to S3 bucket: my-healthcare-bucket
✓ VIT001.png → images/VIT001.png
✓ VIT002.png → images/VIT002.png
✓ SKIN001.png → images/SKIN001.png
...

Upload Summary:
- Successfully uploaded: 45 images
- Skipped (no image file): 3 products
- Failed uploads: 0
- Total time: 12.3 seconds
```

## Troubleshooting

### Common Issues

**"NoCredentialsError: Unable to locate credentials"**
- Solution: Configure AWS credentials using one of the methods in the Setup section

**"Access Denied" errors**
- Solution: Ensure your AWS credentials have `s3:PutObject` permissions for the target bucket

**"No matching image files found"**
- Solution: Check that image filenames exactly match product IDs (case-sensitive)
- Verify the `--images-dir` path is correct

**"Bucket does not exist"**
- Solution: Verify the bucket name is correct and exists in your AWS account
- Check that you're using the correct AWS region

**"AccessControlListNotSupported" errors**
- This error occurs when the S3 bucket has ACLs disabled (a security best practice)
- Solution: The script has been updated to work without ACLs. Public access should be configured through bucket policies in your CDK infrastructure
- The CloudFront distribution will serve the images publicly even if the S3 bucket objects aren't directly public

### Getting Help

1. Run with `--dry-run` first to preview actions
2. Check that your AWS credentials are working: `aws s3 ls`
3. Verify bucket access: `aws s3 ls s3://your-bucket-name`
4. Ensure image files are in the correct directory and properly named

## Integration with CloudFront

Once uploaded, images will be automatically available via CloudFront at:
```
https://your-cloudfront-domain.cloudfront.net/images/PRODUCT_ID.png
```

The CloudFront distribution is configured to:
- Cache images for optimal performance
- Compress images for faster loading
- Serve over HTTPS for security

## File Structure After Upload

```
S3 Bucket
└── images/
    ├── VIT001.png
    ├── VIT002.png
    ├── SKIN001.png
    └── ...
```

Each uploaded image will have:
- **Public read access** for web serving
- **Proper Content-Type** headers
- **Cache-Control** headers for performance
- **Compressed delivery** via CloudFront
