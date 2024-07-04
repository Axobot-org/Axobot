# FROM https://github.com/fictivekin/pyshorturl
# MIT License


import json
from typing import Any
from urllib.parse import urlparse

import requests
from asyncache import cached
from cachetools import TTLCache

BITLY_API_VERSION = "v4"
BITLY_SERVICE_URL = f"https://api-ssl.bitly.com/{BITLY_API_VERSION}/"

class ShortenerServiceError(Exception):
    pass


class BaseShortener():
    """Base class for the url shorteners in the lib"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _do_http_request(self, request_url: str, data: dict=None, headers: dict=None):
        if headers:
            headers = self.headers | headers
        else:
            headers = self.headers

        try:
            if data:
                response = requests.post(request_url, json=data, headers=headers, timeout=10)
            else:
                response = requests.get(request_url, headers=headers, timeout=10)
            return response.status_code, response.content

        except requests.exceptions.HTTPError as err:
            raise ShortenerServiceError(err) from err

    def request(self, action: str, data: dict) -> tuple[int, dict[str, Any]]:
        "Make a request to the API"
        status, response = self._do_http_request(BITLY_SERVICE_URL+action, data)
        return status, json.loads(response)


class BitlyError(ShortenerServiceError):
    pass


class Bitly(BaseShortener):
    "Client class used to shorten and expand URLs using bit.ly API"
    def __init__(self, api_key: str):
        BaseShortener.__init__(self, api_key)

    # pylint: disable=no-self-use
    def _get_error_from_response(self, response: dict[str, Any]) -> str | None:
        """The exact nature of the error is obtained from the 'message' json attribute"""
        return response.get("message")

    @cached(TTLCache(10_000, ttl=86400))
    def shorten_url(self, long_url: str, domain: str="bit.ly"):  # pylint: disable=arguments-differ
        "Shorten a given URL to a bit.ly url"
        params = {
            "long_url": long_url,
            "domain": domain
        }

        status, response = self.request("shorten", params)

        if status >= 400:
            msg = self._get_error_from_response(response)
            raise BitlyError(f"Error occurred while shortening url {long_url}: {msg}")

        short_url: str = response.get("link")
        if not short_url:
            raise BitlyError(f"Error occurred while shortening url {long_url}")
        return short_url

    @cached(TTLCache(10_000, ttl=86400))
    def expand_url(self, short_url: str):
        "Extract a full URL from a given shortened url"
        # Extract info from short_url
        parsed_url = urlparse(short_url)
        params = {
            "bitlink_id": parsed_url.hostname + parsed_url.path
        }

        status, response = self.request("expand", params)

        if status >= 400:
            msg = self._get_error_from_response(response)
            raise BitlyError(f"Error occurred while expanding url {short_url}: {msg}")

        long_url = response.get("long_url")
        if not long_url:
            raise BitlyError(f"Error occurred while expanding url {short_url}")
        return long_url
