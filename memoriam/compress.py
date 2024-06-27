import gzip
import brotli

from memoriam.config import COMPRESS_LEVEL, COMPRESS_MIN_SIZE, COMPRESS_MIMETYPES


class Compress:
    """Brotli/Gzip compression middleware"""

    def __init__(self, app):
        self.app = app

        app.register_middleware(self.compression_middleware, 'response')

    async def compression_middleware(self, request, response):
        accept_encoding = request.headers.get('accept-encoding', '')
        accepted = [item.strip() for item in accept_encoding.split(',')]

        content_length = len(response.body)
        content_type = response.content_type or ''

        if ';' in content_type:
            content_type = content_type.split(';')[0]

        if (200 <= response.status < 300 and
            content_length >= COMPRESS_MIN_SIZE and
            content_type in COMPRESS_MIMETYPES and
            ('br' in accepted or 'gzip' in accepted)):

            if 'br' in accepted:
                response.body = brotli.compress(response.body, quality=COMPRESS_LEVEL)
                response.headers['content-encoding'] = 'br'

            elif 'gzip' in accepted:
                response.body = gzip.compress(response.body, compresslevel=COMPRESS_LEVEL)
                response.headers['content-encoding'] = 'gzip'

            response.headers['content-length'] = len(response.body)

            if vary := response.headers.get('vary'):
                if 'accept-encoding' not in vary.lower():
                    response.headers['vary'] = f'{vary}, Accept-Encoding'
            else:
                response.headers['vary'] = 'Accept-Encoding'

        return response
