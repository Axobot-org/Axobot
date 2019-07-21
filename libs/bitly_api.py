# FROM https://github.com/fictivekin/pyshorturl
# MIT License


import json
import requests

from urllib.parse import urlencode, urlparse

BITLY_API_VERSION = 'v3'
BITLY_SERVICE_URL = 'http://api.bit.ly/%s/' %BITLY_API_VERSION

class ShortenerServiceError(Exception):
    pass


class BaseShortener():
    """Base class for the url shorteners in the lib"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = None

    def _do_http_request(self, request_url, data=None, headers=None):

        if headers:
            self.headers = dict(self.headers.items() + headers.items())

        try:
            if data:
                response = requests.post(request_url, data=data, headers=self.headers)
            else:
                response = requests.get(request_url, headers=self.headers)
            return (response.headers, response.content)

        except requests.exceptions.HTTPError as e:  # pylint: disable=invalid-name
            raise ShortenerServiceError(e)


class BitlyError(ShortenerServiceError):
    pass


class Bitly(BaseShortener):
    def __init__(self, login, api_key):
        BaseShortener.__init__(self, api_key)
        self.login = login
        self.default_request_params = {
            'format': 'json',
            'login':  self.login,
            'apiKey': self.api_key,
        }

    def _get_request_url(self, action, params):
        request_params = self.default_request_params
        request_params.update(params)

        encoded_params = urlencode(request_params)
        return "%s%s?%s" % (BITLY_SERVICE_URL, action, encoded_params)

    def _is_response_success(self, response):  # pylint: disable=no-self-use
        """A successful response will contain:
        a) status_code as 200
        b) status_txt as OK
        """
        return (response.get('status_code') == 200 and
                response.get('status_txt') == 'OK')

    # pylint: disable=inconsistent-return-statements,no-self-use
    def _get_error_from_response(self, response):
        """The exact nature of the error can be obtained from the following
        parameters in the response:

        a) status_code:
             403: Rate Limited.
             503: Unknown Error or Temporaty Unavailability.
             500: Any other invalid request/response.

        b) status_txt:
             MISSING_ARG_%s to denote a missing URL parameter,
             INVALID_%s to denote an invalid value in a request parameter,
        where %s is substituted with the name of the request parameter.

        Note that all valid responses in json and xml format will carry an HTTP
        Response Status Code of 200. This means that invalid, malformed or
        rate-limited json and xml requests may still return an HTTP response
        status code of 200.

        Some examples of error responses extracted from the ApiDocument:
        > json { "status_code": 403, "status_txt": "RATE_LIMIT_EXCEEDED", "data" : null }
        > json { "status_code": 500, "status_txt": "INVALID_URI", "data" : null }
        > json { "status_code": 500, "status_txt": "MISSING_ARG_LOGIN", "data" : null }
        > json { "status_code": 503, "status_txt": "UNKNOWN_ERROR", "data" : null }
        """

        if response.get('status_code') in (403, 500, 503):
            return response.get('status_txt', 'UNKNOWN_ERROR')

        if response.get('status_code') == 200:
            return ('Unknown Error occurred. This could be due to invalid,'
                    ' malformed or rate-limited json')

    def shorten_url(self, long_url, domain='bit.ly'):  # pylint: disable=arguments-differ
        params = {
            'uri':long_url,
            'domain':domain
        }

        request_url = self._get_request_url('shorten', params)
        headers, response = self._do_http_request(request_url)  # pylint: disable=unused-variable
        response = json.loads(response)

        if not self._is_response_success(response):
            msg = self._get_error_from_response(response)
            raise BitlyError('Error occurred while shortening url %s: %s' % (long_url, msg))

        data_dict = response.get('data')
        short_url = data_dict.get('url')
        if not short_url:
            raise BitlyError('Error occurred while shortening url %s' %long_url)
        return short_url


    def expand_url(self, short_url):
        # Extract hash from short_url
        url_path = urlparse(short_url)
        params = {
            'hash':url_path.path[1:]
        }

        request_url = self._get_request_url('expand', params)
        headers, response = self._do_http_request(request_url)  # pylint: disable=unused-variable
        response = json.loads(response)

        if not self._is_response_success(response):
            msg = self._get_error_from_response(response)
            raise BitlyError('Error occurred while expanding url %s: %s' % (short_url, msg))

        data_dict = response.get('data')
        data_dict = data_dict.get('expand')
        long_url = data_dict[0].get('long_url')
        if not long_url:
            raise BitlyError('Error occurred while expanding url %s' %short_url)
        return long_url

    def validate(self, login=None, api_key=None):
        if not login:
            login = self.login
        if not api_key:
            api_key = self.api_key

        params = {
            'x_login':login,
            'x_apiKey':api_key,
        }

        request_url = self._get_request_url('validate', params)
        headers, response = self._do_http_request(request_url)  # pylint: disable=unused-variable
        response = json.loads(response)

        if not self._is_response_success(response):
            msg = self._get_error_from_response(response)
            raise BitlyError('Error occurred while validating account %s: %s' % (self.login, msg))

        data = response.get('data')
        return data.get('valid')
