#!/usr/bin/env python

import sys
import requests
import json
import readline
import re
import isodate
from pprint import pprint

import pdb

from clint.textui import colored, indent, progress, puts


from PIL import Image, ImageOps
import random
from bisect import bisect


def image_to_ascii(image_name):
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

def parse_args_to_dict(arg_list):
    """ Parses list of arguments into a dict with 'params' key -> ordered list
        of params and all other keys -> query argument"""
    arg_dict = {}
    arg_dict['params'] = []
    for arg in arg_list:
        if '=' not in arg:
            arg_dict['params'].append(arg)
        else:
            arg = arg.split('=')
            if len(arg) > 1:
                arg_dict[arg[0]] = arg[1]
    return arg_dict

class Command(object):
    _info_text = "No information provided"
    _base_url = ''
    _options = ['id']
    _params = []
    _arguments = ['id']
    _geolocation_args = []
    _pagination_args = ['per_page', 'page']
    _filtering_args = []
    _sorting_args = ['sort']
    _possible_arguments = {}

    @classmethod
    def get_options(cls):
        return cls._options

    @classmethod
    def get_info_text(cls):
        return cls._info_text

    @classmethod
    def get_params(cls):
        return cls._params

    @classmethod
    def get_arguments(cls):
        return cls._arguments

    @classmethod
    def get_all_possible_arguments(cls):
        pass

    @classmethod
    def validate_arguments(cls, **kwargs):
        all_args = kwargs.iteritems()
        possible_cls_args = cls.get_all_possible_arguments()

        # valid_cls_args = {k:v for k,v in all_args if k in possible_cls_args
        #                   and possible_cls_args[k](v)}

        valid_cls_args = {}
        for k,v in all_args:
            if k in possible_cls_args:
                validate_fn = possible_cls_args[k]
                if validate_fn(v):
                    valid_cls_args[k] = v
                else:
                    raise Exception('%s value: %s is not valid' % (k, v))

        return valid_cls_args


    @classmethod
    def run_command(cls, *args):
        args_dict = parse_args_to_dict(*args)
        args_dict = cls.validate_arguments(**args_dict)
        api_call = cls.construct_api_call(**args_dict)
        call_api_with_results(api_call)

    @classmethod
    def construct_api_call(cls, **kwargs):
        api_route = cls._base_url
        params = kwargs.pop('params', None)
        if params:
            for p in params:
                api_route += '/' + p

        query_args = ['%s=%s'%(k,v) for k,v in kwargs.iteritems()]
        if len(query_args) > 0:
            api_route += '?' + '&'.join(query_args)

        return api_route

class DateTime(object):
    fields = ['datetime_local']

class ExitCommand(Command):
    _info_text = "Exits the program"

    @classmethod
    def run_command(cls, *args):
        yes = set(['yes', 'y', 'ye', ''])
        no = set(['no', 'n'])
        choice = raw_input(colored.yellow('Are you sure you want to exit? [y/n] ')).lower()
        if choice in yes:
            exit()
        elif choice in no:
            return False
        else:
            cls.run_command()


class HelpCommand(Command):
    _info_text = "Returns help information for the program"

    @classmethod
    def run_command(cls, *args):
        requested_keys = { k: True for k in args[0]}.keys()
        all_supported_keys = [x for x in requested_keys if x in supported_commands]

        if len(all_supported_keys):
            # command(s) specified, print help for specified command
            valid_help_keys = all_supported_keys

            print colored.magenta('Parameters can be specified in order they should appear')
            print colored.magenta('Arguments can be specified with "=" between key and value')
            print colored.magenta('\te.g.\tevents 12 geoip=true range=12mi')
            print colored.magenta('\t [PARAMS]: 12 \t [ARGS]: { geoip: true, range: 12mi }')

            for key in valid_help_keys:
                if key == "help":
                    print colored.cyan('  [%s] takes any of the following arguments' % key)
                    all_args = [x for x in supported_commands.keys() if x != "help"]
                    pprint(all_args, indent=8)
                elif key == "events":
                    Event.get_help_text()

                elif supported_commands[key]:
                    print colored.cyan('  [%s] takes any of the following arguments' % key)
                    all_args = supported_commands[key].get_all_arguments()
                    pprint(all_args, indent=8)
        else:
            # print supported commands
            valid_help_keys = supported_commands.keys()

            print colored.blue('  Type `help [command1] [command2] ...` to get more information.\n  The following commands are supported:')
            for key in valid_help_keys:
                print colored.cyan('  [%s] - %s' % (key, supported_commands[key].get_info_text()))



class SetAPIKey(Command):
    _info_text = "Sets the SeatGeek API client key"

    @classmethod
    def get_api_key(cls):
        return _api_key

    @classmethod
    def run_command(cls, *args):
        if len(args[0]) > 0:
            _api_key = args[0][0]
        else:
            raise Exception('no api client key given')

# regexes
def is_numeric(val):
    return re.match('^\d+$', val)

def is_alphabetic(val):
    return re.match('^[A-Za-z]+$', val)

def is_us_state(val):
    return re.match('^(A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|P[AR]|RI|S[CD]|T[NX]|UT|V[AIT]|W[AIVY])$', val)

def is_country_code(val):
    return re.match('^(AF|AX|AL|DZ|AS|AD|AO|AI|AQ|AG|AR|AM|AW|AU|AT|AZ|BS|BH|BD|BB|BY|BE|BZ|BJ|BM|BT|BO|BQ|BA|BW|BV|BR|IO|BN|BG|BF|BI|KH|CM|CA|CV|KY|CF|TD|CL|CN|CX|CC|CO|KM|CG|CD|CK|CR|CI|HR|CU|CW|CY|CZ|DK|DJ|DM|DO|EC|EG|SV|GQ|ER|EE|ET|FK|FO|FJ|FI|FR|GF|PF|TF|GA|GM|GE|DE|GH|GI|GR|GL|GD|GP|GU|GT|GG|GN|GW|GY|HT|HM|VA|HN|HK|HU|IS|IN|ID|IR|IQ|IE|IM|IL|IT|JM|JP|JE|JO|KZ|KE|KI|KP|KR|KW|KG|LA|LV|LB|LS|LR|LY|LI|LT|LU|MO|MK|MG|MW|MY|MV|ML|MT|MH|MQ|MR|MU|YT|MX|FM|MD|MC|MN|ME|MS|MA|MZ|MM|NA|NR|NP|NL|NC|NZ|NI|NE|NG|NU|NF|MP|NO|OM|PK|PW|PS|PA|PG|PY|PE|PH|PN|PL|PT|PR|QA|RE|RO|RU|RW|BL|SH|KN|LC|MF|PM|VC|WS|SM|ST|SA|SN|RS|SC|SL|SG|SX|SK|SI|SB|SO|ZA|GS|SS|ES|LK|SD|SR|SJ|SZ|SE|CH|SY|TW|TJ|TZ|TH|TL|TG|TK|TO|TT|TN|TR|TM|TC|TV|UG|UA|AE|GB|US|UM|UY|UZ|VU|VE|VN|VG|VI|WF|EH|YE|ZM|ZW)$', val)

def is_postal_code(val):
    return re.match('^\d{5}$', val)

def is_datetime(val):
    if isodate.parse_datetime(val) or isodate.parse_date(val):
        return True
    else:
        return False

def is_novalidation(val):
    return True

def is_slug(val):
    return re.match('^[\w\-]+$', val)

def is_encoded_string(val):
    return re.match('^[\w\+]+$', val)


class Event(Command):
    _info_text = "Gets Events and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/events'
    # _params = ['id']
    # _arguments = ['id', 'performers', 'venue', 'datetime', 'q', 'taxonomies']
    # _geolocation_args = ['geoip', 'lat', 'lon', 'range']
    # _filtering_args = ['listing_count', 'average_price', 'lowest_price', 'highest_price']

    _valid_operators = ['gt', 'gte', 'lt', 'lte']

    # nonfull args
    _datetime_args = ['datetime_local', 'datetime_utc']

    _performers_args = ['performers']
    _performers_specs = ['home_team', 'away_team', 'primary', 'any']
    _performers_args_fields = {'id': is_numeric, 'slug': is_slug }

    _venue_args = ['venue']

    # _dependent_args = {
    #     'lat': ('lon'),
    #     'lon': ('lat'),
    #     'range': ('geoip', ['lon', 'lat'])
    #     }

    _possible_args = {
        'params': is_novalidation,
        'id': is_numeric,
        'q': is_encoded_string
        }

    @classmethod
    def get_all_possible_arguments(cls):
        "Gets all possible arguments with corresponding value validation function"

        # pdb.set_trace()
        possible_args = {k:v for k,v in cls._possible_args.iteritems()}

        # add all datetime_args
        for k in ['%s.%s' % (x,y) for x in cls._datetime_args for y in cls._valid_operators]:
            possible_args[k] = is_datetime

        # add all performer args
        for m,n in [('%s.%s' % (x, y), y) for x in cls._performers_args for y in cls._performers_args_fields.keys()]:
            possible_args[m] = cls._performers_args_fields[n]
        # add all performer with specificity
        performer_with_spec = [('%s[%s]' % (x, y)) for x in cls._performers_args for y in cls._performers_specs]
        for m,n in [('%s.%s' % (x,y), y) for x in performer_with_spec for y in cls._performers_args_fields.keys()]:
            possible_args[m] = cls._performers_args_fields[n]

        # add venue args
        venue_external_args = Venue.get_external_args()
        for m,n in [('%s.%s' % (x,y), y) for x in cls._venue_args for y in venue_external_args.keys()]:
            possible_args[m] = venue_external_args[n]

        return possible_args


    @classmethod
    def get_help_text(cls):
        print colored.cyan("The following is a list of all possible arguments for events")
        for k in sorted(cls.get_all_possible_arguments().keys()):
            print "\t <%s>" % k


class Performer(Command):
    _info_text = "Gets Performers and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/performers'
    _params = ['id']
    _arguments = ['id', 'slug', 'q', 'taxonomies']

    fields = ['id', 'slug']

class Venue(Command):
    _info_text = "Gets Venues and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/venues'
    _params = ['id']
    _arguments = ['id', 'city', 'state', 'country', 'postal_code', 'q']
    _geolocation_args = ['geoip', 'lat', 'lon', 'range']

    _possible_args = {
        'params': is_novalidation,
        'id': is_numeric,
        'city': is_alphabetic,
        'state': is_us_state,
        'country': is_country_code,
        'postal_code': is_postal_code,
        'q': is_novalidation
        }

    @classmethod
    def get_external_args(cls):
        return {k:v for k,v in cls._possible_args.iteritems() if k != 'params'}

    fields = ['city', 'id', 'state']

class Taxonomy(Command):
    _info_text = "Gets Taxonomies and returns JSON"

    _base_url = 'http://api.seatgeek.com/2/taxonomies'

    fields = ['name', 'id', 'parent_id']

# # requires Authentication
# class Recommendation(Command):
#     _base_url = 'http://api.seatgeek.com/2/recommendations'

# # requires Authentication
# class RecommendationPerformer(Command):
#     _base_url = 'http://api.seatgeek.com/2/recommendations/performers'


supported_commands = {
    'exit': ExitCommand,
    'help': HelpCommand,
    'events': Event,
    'venues': Venue,
    'performers': Performer,
    'taxonomies': Taxonomy,
    'apikey': SetAPIKey
        }

if __name__ == '__main__':
    image_to_ascii("seatgeek.png")
    # image_to_ascii("seatgeek-logo_300.jpg")
    print colored.blue("Welcome to the SeatGeek API Explorer!")

    while True:
        in_data = raw_input(colored.yellow('>>  ')).strip().split()

        if len(in_data) > 0:
            command = in_data[0]
            if command in supported_commands:
                try:

                    args = in_data[1:]
                    supported_commands[command].run_command(args)

                except Exception, e:
                    print colored.red('<%s>. Please try again.' % e)
            else:
                print colored.red('invalid command')
