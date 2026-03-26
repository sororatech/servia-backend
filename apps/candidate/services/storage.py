import boto3
from botocore.config import Config
from django.conf import settings

def generate_signed_url(file_key, method='put_object', expires_in=900, content_type=None):
    """
    Generate a presigned URL for Cloudflare R2.
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
        region_name='auto',
        config=Config(
            signature_version='s3v4',
        ),
    )
    
    params = {
        'Bucket': settings.CLOUDFLARE_R2_BUCKET,
        'Key': file_key,
    }
    
    if content_type:
        params['ContentType'] = content_type
    
    url = s3.generate_presigned_url(
        ClientMethod=method,
        Params=params,
        ExpiresIn=expires_in,
    )
    
    return url