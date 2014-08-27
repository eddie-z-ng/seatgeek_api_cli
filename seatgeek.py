#!/usr/bin/env python

# import os
# print os.environ

# Print text in all colors

import sys
import requests
import json
import readline

from clint.textui import colored, indent, puts



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
    r = requests.get(url)

    if (r.status_code >= 200 and r.status_code < 300):
        print colored.green(str(r.status_code))
    else:
        print colored.red(str(r.status_code))

    print colored.cyan('Headers:')
    pretty_dict(r.headers)

    parsed_content = json.loads(r.content)
    print colored.magenta('Content:')
    print json.dumps(parsed_content, indent=2, sort_keys=True)


if __name__ == '__main__':

    print "Welcome to the SeatGeek API Explorer!"

    while True:
        in_data = raw_input(colored.yellow('>>  '))

        if len(in_data) != 0:
            print in_data

            call_api_with_results("http://api.seatgeek.com/2/events?venue.state=NY")
