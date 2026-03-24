import boto3
from botocore.config import Config
from django.conf import settings

def generate_signed_url(file_key, method='put_object', expires_in=900, content_type=None):
    """
    Generate a presigned URL for Cloudflare R2.
    
    Args:
        file_key: The S3 key/path for the file
        method: 'put_object' for upload, 'get_object' for download
        expires_in: URL expiry in seconds (default: 15 minutes)
        content_type: MIME type of the file (important for R2 signature)
    
    Returns:
        str: Presigned URL
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
        region_name='auto',  # R2 uses 'auto' region
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},  # R2 requires path-style addressing
        ),
    )
    
    params = {
        'Bucket': settings.CLOUDFLARE_R2_BUCKET,
        'Key': file_key,
    }
    
    # Add Content-Type if provided (CRITICAL for R2 signature matching)
    if content_type:
        params['ContentType'] = content_type
    
    return s3.generate_presigned_url(
        ClientMethod=method,
        Params=params,
        ExpiresIn=expires_in,
        HttpMethod='PUT' if method == 'put_object' else 'GET',
    )