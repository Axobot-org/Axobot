#!/usr/bin/python3

# Copyright (C) 2020  Stefan Vargyas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SOURCE: https://gist.github.com/stvar/f57e9792c3dc49fab2690247d6ee74de

import os
import sys
from argparse import ArgumentParser, HelpFormatter, Namespace
from functools import wraps
from typing import Callable, Iterable, Optional

from google.auth.exceptions import GoogleAuthError
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

program = os.path.basename(sys.argv[0])
VER_DATE = '0.1 2020-07-25 11:23'  # $ date +'%F %R'


def error(msg: str, *args):
    "Print an error message in the console"
    if len(args) > 0:
        msg = msg % args
    print("%s: error: %s" % (program, msg), file=sys.stderr)
    sys.exit(1)


def warn(msg: str, *args):
    "Print a warning message in the console"
    if len(args) > 0:
        msg = msg % args
    print("%s: warning: %s", (program, msg), file=sys.stderr)


def print_list(lst: Iterable, name: str = None, newline=False):
    "Print a list of any object in the console"
    if len(lst) > 0:
        if newline:
            print('\n')
        if name:
            print(name)
        print('\n'.join(lst))


class Text:
    "Static class used to normalize texts and compare them"

    # pylint: disable=import-outside-toplevel
    from unicodedata import normalize

    # https://stackoverflow.com/a/29247821/8327971

    @staticmethod
    def normalize_casefold(text: str):
        return Text.normalize("NFKD", text.casefold())

    @staticmethod
    def casefold_equal(text1: str, text2: str):
        return \
            Text.normalize_casefold(text1) == \
            Text.normalize_casefold(text2)


class Service:
    "Base class used to make requests to the YouTube API"

    # pylint: disable=import-outside-toplevel
    from googleapiclient.discovery import build

    def __init__(self, max_results, app_key):
        self.youtube: Resource = Service.build(
            'youtube', 'v3', developerKey=app_key)
        self.max_results = max_results

    def search_term(self, term, search_type=None) -> tuple[list[str], list[str], list[str]]:
        "Search for a specific term in the YouTube API"
        resp = self.youtube.search().list(  # pylint: disable=no-member
            q=term,
            type=search_type,
            part='id,snippet',
            fields='items(id,snippet(title))',
            maxResults=self.max_results
        ).execute()

        items = resp['items']
        if len(items) > self.max_results:
            warn('more than %d results found when querying search API (%s results)', self.max_results, len(items))
            items = items[:self.max_results]

        res = [], [], []

        for item in items:
            k = item['id']['kind']
            if k == 'youtube#video':
                i, k = 0, 'videoId'
            elif k == 'youtube#channel':
                i, k = 1, 'channelId'
            elif k == 'youtube#playlist':
                i, k = 2, 'playlistId'
            else:
                assert False

            res[i].append('%s: %s' % (
                item['id'][k], item['snippet']['title']))

        return res

    def find_channel_by_custom_url(self, url: str) -> Optional[str]:
        "Search for a channel ID from a given custom identifier"
        resp = self.youtube.search().list(  # pylint: disable=no-member
            q=url,
            part='id',
            type='channel',
            fields='items(id(kind,channelId))',
            maxResults=self.max_results
        ).execute()

        items = resp['items']
        assert len(items) <= self.max_results

        channels = []
        for item in items:
            assert item['id']['kind'] == 'youtube#channel'
            channels.append(item['id']['channelId'])

        if len(channels) == 0:
            return None

        resp = self.youtube.channels().list(  # pylint: disable=no-member
            id=','.join(channels),
            part='id,snippet',
            fields='items(id,snippet(customUrl))',
            maxResults=len(channels)
        ).execute()

        items = resp['items']
        assert len(items) <= len(channels)

        for item in items:
            cust = item['snippet'].get('customUrl')
            if cust is not None and Text.casefold_equal(cust, url):
                assert item['id'] is not None
                return item['id']

        return None

    def find_channel_by_user_name(self, user: str) -> Optional[str]:
        "Search for a channel ID from a given username"
        resp = self.youtube.channels().list(  # pylint: disable=no-member
            forUsername=user,
            part='id',
            fields='items(id)',
            maxResults=1
        ).execute()

        # stev: 'items' may be absent
        items = resp.get('items', [])
        assert len(items) <= 1

        for item in items:
            assert item['id'] is not None
            return item['id']

        return None

    def query_custom_url(self, channel_id: str) -> Optional[str]:
        "Search for a custom URL from a given channel identifier"
        resp = self.youtube.channels().list(  # pylint: disable=no-member
            id=channel_id,
            part='snippet',
            fields='items(snippet(customUrl))',
            maxResults=1
        ).execute()

        # stev: 'items' may be absent
        items = resp.get('items', [])
        assert len(items) <= 1

        for item in items:
            if 'customUrl' in item['snippet']:
                return item['snippet']['customUrl']
        return None

    def query_channel_title(self, channel_id: str) -> Optional[str]:
        "Search for a custom URL from a given channel identifier"
        resp = self.youtube.channels().list(  # pylint: disable=no-member
            id=channel_id,
            part='snippet',
            fields='items(snippet(title))',
            maxResults=1
        ).execute()

        # stev: 'items' may be absent
        items = resp.get('items', [])
        assert len(items) <= 1

        for item in items:
            if 'title' in item['snippet']:
                return item['snippet']['title']
        return None


def service_func(func):
    "Handle Google errors while requesting an information"
    @wraps(func)
    def wrapper(*arg, **kwd):
        try:
            return func(*arg, **kwd)
        except HttpError as err:
            error('HTTP error: %s', err)
        except GoogleAuthError as err:
            error('Google auth error: %s', err)
        return None

    return wrapper

class Act:
    "Class used to process a specific action based on the user input (running arguments)"

    @staticmethod
    @service_func
    def search_term(opts: Namespace):
        "Search for a term in the API"
        service = Service(
            opts.max_results,
            opts.app_key)

        videos, channels, playlists = service.search_term(opts.search_term, opts.type)

        result_type = not opts.type or None

        print_list(videos, result_type and 'Videos')
        print_list(channels, result_type and 'Channels', bool(videos))
        print_list(playlists, result_type and 'Playlists', bool(videos) or bool(channels))

    @staticmethod
    @service_func
    def find_channel(opts: Namespace, name: str):
        "Find a channel from its username or custom URL, execute the corresponding Service method and print the result"
        service = Service(
            opts.max_results,
            opts.app_key)

        lowered_name = name.lower().replace(' ', '_')
        arg: str = getattr(opts, lowered_name)
        result: Optional[str] = getattr(service, 'find_channel_by_' + lowered_name)(arg)

        if result is None:
            error('%s "%s": no associated channel found',
                name, arg)
        else:
            print(result)

    find_channel_by_custom_url: Callable[[Namespace], None] = \
        lambda opts: Act.find_channel(opts, 'custom URL')

    find_channel_by_user_name: Callable[[Namespace], None] = \
        lambda opts: Act.find_channel(opts, 'user name')

    @staticmethod
    @service_func
    def query_channel_custom_url(opts: Namespace):
        "Find a custom channel name from its identifier and print the result"
        service = Service(
            opts.max_results,
            opts.app_key)

        custom_name: Optional[str] = service.query_custom_url(opts.channel_url)

        if custom_name is not None:
            print(custom_name)

    @staticmethod
    @service_func
    def query_channel_title(opts: Namespace):
        "Find a custom channel name from its identifier and print the result"
        service = Service(
            opts.max_results,
            opts.app_key)

        title: Optional[str] = service.query_channel_title(opts.channel_url)

        if title is not None:
            print(title)


def options():
    "Define which action to call according to user input (from running arguments)"

    class Formatter(HelpFormatter):
        "Custom arguments formatter to avoid showing long options twice"

        def _format_action_invocation(self, action):
            # https://stackoverflow.com/a/31124505/8327971
            meta = self._get_default_metavar_for_optional(action)
            return '|'.join(action.option_strings) + ' ' + self._format_args(action, meta)

    parser = ArgumentParser(
        formatter_class=Formatter,
        add_help=False)
    parser.error = error

    STR = 'STR'  # pylint: disable=invalid-name
    NUM = 'NUM'  # pylint: disable=invalid-name

    def uint(arg):
        "Define a positive or null integer type"
        result = int(arg)
        if result <= 0:
            raise ValueError()
        return result

    # stev: action options:
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument('-s', '--search-term',
        help = 'do search for the given term',
        metavar = STR, default = None)
    group.add_argument('-c', '--custom-url',
        help = 'do find the channel ID associated to the given custom URL',
        metavar = STR, default = None)
    group.add_argument('-u', '--user-name',
        help = 'do find the channel ID associated to the given user name',
        metavar = STR, default = None)
    group.add_argument('-l', '--channel-url',
        help = 'do query the custom URL associated to the given channel',
        metavar = STR, default = None)
    # stev: dependent options:
    parser.add_argument('-t', '--type', choices = ('channel', 'playlist', 'video'),
        help = 'restrict the search query to only retrieve the specified type of resource',
        default = None)
    parser.add_argument('-m', '--max-results', type = uint,
        help = 'set the API endpoint parameter `maxResults\' to the given number (default: 10)',
        metavar = NUM, default = 10)
    parser.add_argument('-k', '--app-key',
        help = 'YouTube Data API application key (default: $YOUTUBE_DATA_APP_KEY)',
        metavar = STR, default = None)
    # stev: info options:
    parser.add_argument('-v', '--version',
        action = 'version', version = '%(prog)s: version ' + VER_DATE,
        help = 'print version numbers and exit')
    parser.add_argument('-h', '--help',
        help = 'display this help info and exit',
        action = 'help')

    args = parser.parse_args()

    if args.app_key is None:
        args.app_key = os.getenv('YOUTUBE_DATA_APP_KEY')
        if args.app_key is None:
            error('application key not given')

    has_search_terms = bool(args.search_term)
    has_custom_name = bool(args.custom_url)
    has_user_name = bool(args.user_name)
    has_channel_url = bool(args.channel_url)
    assert has_search_terms + has_custom_name + has_user_name + has_channel_url == 1

    if has_search_terms:
        args.action = Act.search_term
    elif has_custom_name:
        args.action = Act.find_channel_by_custom_url
    elif has_user_name:
        args.action = Act.find_channel_by_user_name
    elif has_channel_url:
        args.action = Act.query_channel_custom_url
    else:
        assert False

    return args


def main():
    opt = options()
    opt.action(opt)


if __name__ == '__main__':
    main()
