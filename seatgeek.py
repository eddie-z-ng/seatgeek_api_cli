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
    _default_args = {}

    @classmethod
    def get_info_text(cls):
        return cls._info_text

    @classmethod
    def get_all_default_args(cls):
        possible_args = {k:v for k,v in cls._default_args.iteritems()}
        return possible_args

    @classmethod
    def get_help_text(cls, **kwargs):
        all_possible_args = sorted(cls.get_all_default_args().keys())
        name = kwargs.get('name', cls.__name__)
        if len(all_possible_args) > 0:
            print colored.cyan("Possible arguments for %s: " % name)
            for k in sorted(cls.get_all_default_args().keys()):
                print "\t <%s>" % k
        else:
            print colored.cyan("No arguments needed for %s" % name)

    @classmethod
    def validate_arguments(cls, **kwargs):
        all_args = kwargs.iteritems()
        possible_cls_args = cls.get_all_default_args()

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
            print colored.magenta('\te.g.\tevents 12 venue.state=NY')
            print colored.magenta('\t [PARAMS]: 12 \t [ARGS]: { "venue.state": "NY" }')

            for key in valid_help_keys:
                if key == "help":
                    print colored.cyan('  [%s] takes any of the following arguments' % key)
                    all_args = [x for x in supported_commands.keys() if x != "help"]
                    pprint(all_args, indent=8)

                elif supported_commands[key]:
                    supported_commands[key].get_help_text(name=key)
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

# validation functions
def is_geoip(val):
    if is_postal_code(val):
        return True
    if is_bool_str(val):
        return True
    return re.match('^(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))\.(\d|[1-9]\d|1\d\d|2([0-4]\d|5[0-5]))$', val)

def is_bool_str(val):
    return re.match('^true|false$', val)

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
    try:
        if isodate.parse_datetime(val):
            return True
    except Exception, e:
        pass
    try:
        if isodate.parse_date(val):
            return True
    except Exception, e:
        pass

    return False

def is_novalidation(val):
    return True

def is_slug(val):
    return re.match('^[\w\-]+$', val)

def is_encoded_string(val):
    return re.match('^[\w\+]+$', val)

def is_sg_sort_with_date(val):
    sort_fields = ['datetime_local', 'datetime_utc', 'announce_date', 'id', 'score']
    valid_sort_params = is_sg_sort_helper(sort_fields)
    return val in valid_sort_params

def is_sg_sort(val):
    sort_fields = ['id', 'score']
    valid_sort_params = is_sg_sort_helper(sort_fields)
    return val in valid_sort_params

def is_sg_sort_helper(sort_fields):
    sort_directions = ['asc', 'desc']
    valid_sort_params = ['%s.%s' % (x,y) for x in sort_fields for y in sort_directions]
    return valid_sort_params

def is_lat_deg(val):
    # ranges from -90.0 to 90.0
    return re.match('^([-]?\d{1,2}([.]\d+)?)$', val)

def is_lon_deg(val):
    # ranges from -180.0 to 180.0
    return re.match('^([-]?\d{1,3}([.]\d+)?)$', val)

def is_range_str(val):
    return re.match('^(\d+(km|mi))$', val)

# class DependentArg(object):
#     _exclusives = {
#         'geoip': ['lat', 'lon'],
#         'lat': ['geoip'],
#         'lon': ['geoip']
#     }

#     _dependents = {
#         'lat': ['lon'],
#         'lon': ['lat'],
#         'range': ['']
#     }

def merge_keys_across_fields(base_dict, end_dict, base_list):
    for m,n in [('%s.%s' % (x, y), y) for x in base_list for y in end_dict.keys()]:
        base_dict[m] = end_dict[n]

class Event(Command):
    _info_text = "Gets Events and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/events'

    # _dependent_args = {
    #     'lat': ('lon'),
    #     'lon': ('lat')
    #     'range': ('geoip')
    #     }

    _valid_operators = ['gt', 'gte', 'lt', 'lte']
    _filtering_args = ['listing_count', 'average_price', 'lowest_price', 'highest_price']
    _datetime_args = ['datetime_local', 'datetime_utc']

    _performers_args = ['performers']
    _performers_specs = ['home_team', 'away_team', 'primary', 'any']
    _performers_args_fields = {'id': is_numeric, 'slug': is_slug }

    _venue_args = ['venue']
    _taxonomies_args = ['taxonomies']

    _default_args = {
        'params': is_novalidation,
        'id': is_numeric,
        'q': is_encoded_string,
        'per_page': is_numeric,
        'page': is_numeric,
        'sort': is_sg_sort_with_date,
        'aid': is_numeric,
        'rid': is_numeric,
        'geoip': is_geoip,
        'lat': is_lat_deg,
        'lon': is_lon_deg,
        'range': is_range_str
        }

    @classmethod
    def get_all_default_args(cls):
        "Gets all possible arguments with corresponding value validation function"

        # get all default possible arguments
        possible_args = super(Event,cls).get_all_default_args()

        # add all filtering_args -- should be numeric
        for k in ['%s.%s' % (x,y) for x in cls._filtering_args for y in cls._valid_operators]:
            possible_args[k] = is_numeric

        # add all datetime_args -- should be datetime
        for k in cls._datetime_args:
            possible_args[k] = is_datetime
        for k in ['%s.%s' % (x,y) for x in cls._datetime_args for y in cls._valid_operators]:
            possible_args[k] = is_datetime

        # add all performer args
        merge_keys_across_fields(possible_args, cls._performers_args_fields, cls._performers_args)

        # add all performer with specificity
        performer_with_spec = [('%s[%s]' % (x, y)) for x in cls._performers_args for y in cls._performers_specs]
        merge_keys_across_fields(possible_args, cls._performers_args_fields, performer_with_spec)

        # add all venue args
        venue_external_args = Venue.get_external_args()
        merge_keys_across_fields(possible_args, venue_external_args, cls._venue_args)

        # add all taxonomies args
        taxonomies_external_args = Taxonomy.get_external_args()
        merge_keys_across_fields(possible_args, taxonomies_external_args, cls._taxonomies_args)

        return possible_args


class Performer(Command):
    _info_text = "Gets Performers and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/performers'

    _taxonomies_args = ['taxonomies']

    _default_args = {
        'params': is_novalidation,
        'id': is_numeric,
        'slug': is_slug,
        'q': is_encoded_string,
        'per_page': is_numeric,
        'page': is_numeric,
        'sort': is_sg_sort,
        'aid': is_numeric,
        'rid': is_numeric
    }

    @classmethod
    def get_all_default_args(cls):
        "Gets all possible arguments with corresponding value validation function"

        # get all default possible arguments
        possible_args = super(Performer, cls).get_all_default_args()

        # add all taxonomies args
        taxonomies_external_args = Taxonomy.get_external_args()
        merge_keys_across_fields(possible_args, taxonomies_external_args, cls._taxonomies_args)

        return possible_args

class Venue(Command):
    _info_text = "Gets Venues and returns JSON"
    _base_url = 'http://api.seatgeek.com/2/venues'

    _default_args = {
        'params': is_novalidation,
        'id': is_numeric,
        'city': is_alphabetic,
        'state': is_us_state,
        'country': is_country_code,
        'postal_code': is_postal_code,
        'q': is_novalidation,
        'per_page': is_numeric,
        'page': is_numeric,
        'sort': is_sg_sort,
        'aid': is_numeric,
        'rid': is_numeric
        }

    @classmethod
    def get_external_args(cls):
        return {k:v for k,v in cls._default_args.iteritems() if k != 'params'}


class Taxonomy(Command):
    _info_text = "Gets Taxonomies and returns JSON"

    _base_url = 'http://api.seatgeek.com/2/taxonomies'

    _default_args = {}
    _external_args_fields = { 'parent_id': is_numeric, 'id': is_numeric, 'name': is_alphabetic}

    @classmethod
    def get_external_args(cls):
        return {k:v for k,v in cls._external_args_fields.iteritems()}


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
