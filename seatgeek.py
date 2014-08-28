#!/usr/bin/env python

import sys
import requests
import json
import readline
import re

from clint.textui import colored, indent, progress, puts


from PIL import Image, ImageOps
import random
from bisect import bisect

# image to ascii adopted from Steven Kay's implementation:
# http://stevendkay.wordpress.com/2009/09/08/generating-ascii-art-from-photographs-in-python/

# greyscale.. the following strings represent
# 7 tonal ranges, from lighter to darker.
# for a given pixel tonal level, choose a character
# at random from that range.

greyscale = [
            " ",
            " ",
            ".,-",
            "_ivc=!/|\\~",
            "gjez2]/(YL)t[+T7Vf",
            "mdK4ZGbNDXY5P*Q",
            "W8KMA",
            "#%$"
            ]

# using the bisect class to put luminosity values
# in various ranges.
# these are the luminosity cut-off points for each
# of the 7 tonal levels. At the moment, these are 7 bands
# of even width, but they could be changed to boost
# contrast or change gamma, for example.

zonebounds = [36, 72, 108, 144, 180, 216, 252]

# open image and resize
# experiment with aspect ratios according to font


def image_to_ascii(image_name):
    im=Image.open(image_name)
    width, height = im.size
    new_width = 80
    new_height = int((height * new_width) / width)
    im = im.resize((new_width, new_height))
    im = im.convert("L") # convert to mono

    # now, work our way over the pixels

    ascii_img=""
    for y in range(0,im.size[1]):
        for x in range(0,im.size[0]):
            lum=255-im.getpixel((x,y))
            row=bisect(zonebounds,lum)
            possibles=greyscale[row]
            ascii_img=ascii_img+possibles[random.randint(0,len(possibles)-1)]
        ascii_img=ascii_img+"\n"

    print ascii_img


def pretty_dict(d):
    def pretty(d, indent):
        #two spaces
        space = '  '
        for i, (key, value) in enumerate(iter(sorted(d.iteritems()))):
            if isinstance(value, dict):
                print '{0}"{1}": {{'.format( space * indent, str(key))
                pretty(value, indent+1)
                if i == len(d)-1:
                    print '{0}}}'.format( space * indent)
                else:
                    print '{0}}},'.format( space * indent)
            else:
                if i == len(d)-1:
                    print '{0}"{1}": "{2}"'.format( space * indent, str(key), value)
                else:
                    print '{0}"{1}": "{2}",'.format( space * indent, str(key), value)
    print '{'
    pretty(d,indent=1)
    print '}'

def call_api_with_results(url):
    print colored.cyan("Making request: %s" % (url))
    r = requests.get(url, stream=True, timeout=5)

    if r.headers.get('content-length'):
        total_length = int(r.headers.get('content-length'))
        content = ''
        for chunk in progress.bar(r.iter_content(chunk_size=1024),
                                                 expected_size=(total_length/1024) + 1,
                                                 label=colored.green("  KB received: ")):
            content += chunk
    else:
        content = r.content

    if (r.status_code >= 200 and r.status_code < 300):
        print 'Status Code: %s' % colored.green(str(r.status_code))
    else:
        print 'Status Code: %s' % colored.red(str(r.status_code))

    print colored.cyan('Headers:')
    pretty_dict(r.headers)

    parsed_content = json.loads(content)
    print colored.magenta('Content:')
    print json.dumps(parsed_content, indent=2, sort_keys=True)


class Command(object):
    _base_url = ''
    _options = ['id']
    _params = []
    _arguments = ['id']
    _geolocation_args = []
    _pagination_args = ['per_page', 'page']
    _filtering_args = []
    _sorting_args = ['sort']

    @classmethod
    def get_options(cls):
        return cls._options

    @classmethod
    def get_params(cls):
        return cls._params

    @classmethod
    def get_arguments(cls):
        return cls._arguments

    @classmethod
    def get_all_arguments(cls):
        return cls._arguments + cls._geolocation_args + cls._pagination_args + cls._sorting_args

    @classmethod
    def whitelist_arguments(cls, **kwargs):
        if 'param_id' in kwargs:
            if not re.match('^\d+$', kwargs['param_id']):
                raise Exception('invalid param id: %s. Numeric values only' % kwargs['param_id'])
        else:

            for key, value in kwargs.iteritems():
                if (key not in cls._arguments and
                   key not in cls._geolocation_arguments and
                   key not in cls._pagination_args and
                   key not in cls._sorting_args):
                    raise Exception('invalid argument: <%s: %s>' % (key, value))

    @classmethod
    def construct_api_call(cls, **kwargs):
        api_route = cls._base_url
        param_id = kwargs.pop('param_id', None)
        if param_id:
            api_route += '/' + param_id
        else:
            query_args = ['%s=%s'%(k,v) for k,v in kwargs.iteritems()]
            if len(query_args) > 0:
                api_route += '?' + '&'.join(query_args)

        return api_route

class DateTime(object):
    fields = ['datetime_local']

class Event(Command):
    _base_url = 'http://api.seatgeek.com/2/events'
    _params = ['id']
    _arguments = ['id', 'performers', 'venue', 'datetime', 'q', 'taxonomies']
    _geolocation_args = ['geoip', 'lat', 'lon', 'range']
    _filtering_args = ['listing_count', 'average_price', 'lowest_price', 'highest_price']

class Performer(Command):
    _base_url = 'http://api.seatgeek.com/2/performers'
    _params = ['id']
    _arguments = ['id', 'slug', 'q', 'taxonomies']

    fields = ['id', 'slug']

class Venue(Command):
    _base_url = 'http://api.seatgeek.com/2/venues'
    _params = ['id']
    _arguments = ['id', 'city', 'state', 'country', 'postal_code', 'q']
    _geolocation_args = ['geoip', 'lat', 'lon', 'range']

    fields = ['city', 'id', 'state']

class Taxonomy(Command):
    _base_url = 'http://api.seatgeek.com/2/taxonomies'

    fields = ['name', 'id', 'parent_id']

# # requires Authentication
# class Recommendation(Command):
#     _base_url = 'http://api.seatgeek.com/2/recommendations'

# # requires Authentication
# class RecommendationPerformer(Command):
#     _base_url = 'http://api.seatgeek.com/2/recommendations/performers'


def get_help():
    for key in supported_commands.keys():
        print colored.magenta('\t%s' % key)

def get_events(**kwargs):
    Event.whitelist_arguments()
    api_call = Event.construct_api_call(**args_dict)
    call_api_with_results(api_call)

def get_venues(**kwargs):
    Venue.whitelist_arguments()
    api_call = Venue.construct_api_call(**args_dict)
    call_api_with_results(api_call)

def get_performers(**kwargs):
    Performer.whitelist_arguments()
    api_call = Performer.construct_api_call(**args_dict)
    call_api_with_results(api_call)

def get_taxonomies(**kwargs):
    Taxonomy.whitelist_arguments()
    api_call = Taxonomy.construct_api_call(**args_dict)
    call_api_with_results(api_call)

def prompt_exit():
    yes = set(['yes', 'y', 'ye', ''])
    no = set(['no', 'n'])
    choice = raw_input(colored.yellow('Are you sure you want to exit? [y/n] ')).lower()
    if choice in yes:
        exit()
    elif choice in no:
        return False
    else:
        prompt_exit()

supported_commands = {
    'exit': prompt_exit,
    'help': get_help,
    'events': get_events,
    'venues': get_venues,
    'performers': get_performers,
    'taxonomies': get_taxonomies
        }

def parse_args_to_dict(arg_list):
    arg_dict = {}
    for arg in arg_list:
        if '=' not in arg:
            arg_dict['param_id'] = arg
        else:
            arg = arg.split('=')
            arg_dict[arg[0]] = arg[1]
    return arg_dict

if __name__ == '__main__':
    image_to_ascii("seatgeek.png")
    # image_to_ascii("seatgeek-logo_300.jpg")
    print "Welcome to the SeatGeek API Explorer!"

    while True:
        in_data = raw_input(colored.yellow('>>  ')).strip().split()

        if len(in_data) != 0:
            command = in_data[0]

            if command in supported_commands:

                try:
                    args_dict = {}
                    if len(in_data) > 1:
                        actual_args = in_data[1:]
                        args_dict = parse_args_to_dict(actual_args)

                    supported_commands[command](**args_dict)

                except Exception, e:
                    print colored.red('Exception: %s. Please try again.' % e)
            else:
                print colored.red('invalid command')
