#!/usr/bin/env python

# import os
# print os.environ

# Print text in all colors

import sys
import requests
import json
import readline

from clint.textui import colored, indent, progress, puts

from time import sleep
from random import random


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
    total_length = int(r.headers.get('content-length'))
    content = ''
    for chunk in progress.bar(r.iter_content(chunk_size=1024),
                                             expected_size=(total_length/1024) + 1,
                                             label=colored.green("  KB received: ")):
        content += chunk

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
    _options = ['id']
    @classmethod
    def get_options(cls):
        return cls._options

class Event(Command):
    _options = ['id', 'date', 'name']

class Performer(Command):
    _options = ['id', 'date', 'name']

class Venue(Command):
    _options = ['id', 'date', 'name']


supported_commands = { 'events': Event }

if __name__ == '__main__':

    print "Welcome to the SeatGeek API Explorer!"

    while True:
        in_data = raw_input(colored.yellow('>>  ')).strip().split()

        if len(in_data) != 0:
            command = in_data[0]

            if command in supported_commands:

                print supported_commands[command].get_options()

                try:
                    call_api_with_results("http://api.seatgeek.com/2/events?venue.state=NY")

                except Exception, e:
                    print colored.red('Exception: %s. Please try again.' % e)
            else:
                print colored.red('invalid command')
