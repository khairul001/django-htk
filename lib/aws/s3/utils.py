import re
import time

from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
from boto.s3.key import Key

# AWSCredentials should be available in settings.CREDENTIALS_DIR
import AWSCredentials

from htk.lib.aws.s3.cachekeys import S3UrlCache
from htk.constants.time import *

class S3Manager(object):
    """S3Manager is an interface/wrapper for boto to Amazon S3
    """
    def __init__(self):
        self.access_key = AWSCredentials.HEADLESS_S3_ACCESS_KEY
        self.secret_key = AWSCredentials.HEADLESS_S3_SECRET_KEY
        self._connect()

    def _connect(self):
        self.conn = S3Connection(self.access_key, self.secret_key)

    def _get_bucket(self, bucket_id):
        """Returns a boto.s3.bucket.Bucket object pointing at S3:bucket-id
        """
        try:
            bucket = self.conn.get_bucket(bucket_id)
        except S3ResponseError:
            bucket = None
        return bucket

    def _get_key(self, bucket_id, key_id):
        """Returns a boto.s3.key.Key object pointing at S3:bucket-id/key-id
        """
        bucket = self._get_bucket(bucket_id)
        if bucket:
            key = Key(bucket)
            key.key = key_id
        else:
            key = None
        return key

    def put_file(self, bucket_id, key_id, f):
        """Stores a file
        """
        key = self._get_key(bucket_id, key_id)
        if key:
            bytes_written = key.set_contents_from_file(f)
        else:
            bytes_written = 0
        return bytes_written

    def delete_file(self, bucket_id, key_id):
        """Deletes a file
        """
        key = self._get_key(bucket_id, key_id)
        was_deleted = False
        if key:
            key.delete()
            was_deleted = True
        return was_deleted

    def get_url(self, bucket_id, key_id, expiration=3600, cache=False):
        """Generates the URL for a file

        `expiration` how long we should request for
        `cache` if we should read/write the value from/to cache
        """
        if cache:
            prekey = [bucket_id, key_id,]
            c = S3UrlCache(prekey)
            url = c.get()
        else:
            url = None

        if url is None:
            key = self._get_key(bucket_id, key_id)
            if key:
                url = key.generate_url(expiration)
                if cache:
                    # need to check the actual URL expiration
                    expiration_match = re.match(r'.*&Expires=(\d)+&.*', url)
                    if expiration_match:
                        expires_at = expiration_match.group(1)
                        # request slightly shorter cache duration to have a buffer; at least 1 minute
                        duration = max(int(expires_at) - int(time.time()) - TIMEOUT_5_MINUTES, TIMEOUT_1_MINUTE)
                    else:
                        duration = None
                    c.cache_store(url, duration)
            else:
                url = None
        return url
