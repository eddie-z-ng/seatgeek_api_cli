#!/usr/bin/env python

# import os
# print os.environ

# Print text in all colors

from clint.textui import colored, puts

if __name__ == '__main__':
  for color in colored.COLORS:
    puts(getattr(colored,color)('Text in {0:s}'.format(color.upper())))