# -*- coding: utf-8 -*-
#
# Copyright (c) 2016-2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint:  disable=C0103, C0301

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import sys
import collections
import re

from . import erring
from . import tooling
from . import coding
from . import re_patterns
from . import grammar

# pylint:  disable=W0622
if sys.maxunicode == 0xFFFF:
    chr = coding.chr_surrogate
    ord = coding.ord_surrogate
# pylint:  enable=W0622


NEWLINE = grammar.LIT_GRAMMAR['newline']




def basic_unicode_escape(code_point):
    '''
    Basic backslash-escape.  Useful for creating error messages, etc.
    '''
    n = ord(code_point)
    if n <= 0xFFFF:
        return '\\u{0:04x}'.format(n)
    return '\\U{0:08x}'.format(n)




class Escape(object):
    '''
    Replace code points and bytes in Unicode strings and byte strings with
    their escaped equivalents when they cannot be represented literally.
    '''
    def __init__(self, only_ascii=False, brace_escapes=True, x_escapes=True):
        if not all(opt in (True, False) for opt in (only_ascii, brace_escapes, x_escapes)):
            raise TypeError
        self.only_ascii = only_ascii
        self.brace_escapes = brace_escapes
        self.x_escapes = x_escapes


        # Set function for escaping Unicode characters, based on whether
        # `\xHH` escapes are allowed and whether `\u{HHHHHH}` escapes are in
        # use.  There are no such conditions for the binary equivalent, since
        # only `\xHH` is allowed in that case.
        if x_escapes and brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xubrace
        elif x_escapes:
            self._escape_unicode_char = self._escape_unicode_char_xuU
        elif brace_escapes:
            self._escape_unicode_char = self._escape_unicode_char_ubrace
        else:
            self._escape_unicode_char = self._escape_unicode_char_uU


        # Dict for escaping code points that may not appear literally.  Code
        # points are detected with a regex, and their escaped replacements
        # are then looked up in the dict.  The dict serves to memoize the
        # escape function.
        self._escape_unicode_dict = tooling.keydefaultdict(self._escape_unicode_char)
        self._escape_unicode_dict.update(grammar.SHORT_BACKSLASH_ESCAPES)

        # The bytes escape dict is similar to the Unicode equivalent, but
        # involves a small enough range that it can be fully prepopulated.
        self._escape_bytes_dict = {chr(n).encode('latin1'): '\\x{0:02x}'.format(n).encode('ascii') for n in range(256)}
        self._escape_bytes_dict.update({k.encode('ascii'): v.encode('ascii') for k, v in grammar.SHORT_BACKSLASH_ESCAPES})


        # Regexes for finding code points and bytes that must be escaped.
        # Code points other than invalid literals are put first, since they
        # will typically come up more frequently.
        pattern_dict = {'not_valid_literal_ascii': re_patterns.NOT_VALID_LITERAL_ASCII,
                        'not_valid_literal_unicode': re_patterns.NOT_VALID_LITERAL_ASCII if self.only_ascii else re_patterns.NOT_VALID_LITERAL,
                        'backslash': grammar.RE_GRAMMAR['backslash'],
                        'singlequote': grammar.RE_GRAMMAR['escaped_string_singlequote_delim'],
                        'doublequote': grammar.RE_GRAMMAR['escaped_string_doublequote_delim'],
                        'newline': NEWLINE}

        invalid_literal_or_backslash_singlequote_newline_unicode_re_pattern = '{backslash}|{singlequote}|{newline}|{not_valid_literal_unicode}'.format(**pattern_dict)
        self._invalid_literal_or_backslash_singlequote_newline_unicode_re = re.compile(invalid_literal_or_backslash_singlequote_newline_unicode_re_pattern)
        invalid_literal_or_backslash_doublequote_newline_unicode_re_pattern = '{backslash}|{doublequote}|{newline}|{not_valid_literal_unicode}'.format(**pattern_dict)
        self._invalid_literal_or_backslash_doublequote_newline_unicode_re = re.compile(invalid_literal_or_backslash_doublequote_newline_unicode_re_pattern)

        invalid_literal_or_backslash_singlequote_unicode_re_pattern = '{backslash}|{singlequote}|{not_valid_literal_unicode}'.format(**pattern_dict)
        self._invalid_literal_or_backslash_singlequote_unicode_re = re.compile(invalid_literal_or_backslash_singlequote_unicode_re_pattern)
        invalid_literal_or_backslash_doublequote_unicode_re_pattern = '{backslash}|{doublequote}|{not_valid_literal_unicode}'.format(**pattern_dict)
        self._invalid_literal_or_backslash_doublequote_unicode_re = re.compile(invalid_literal_or_backslash_doublequote_unicode_re_pattern)

        invalid_literal_or_backslash_singlequote_newline_bytes_re_pattern = '{backslash}|{singlequote}|{newline}|{not_valid_literal_ascii}'.format(**pattern_dict).encode('ascii')
        self._invalid_literal_or_backslash_singlequote_newline_bytes_re = re.compile(invalid_literal_or_backslash_singlequote_newline_bytes_re_pattern)
        invalid_literal_or_backslash_doublequote_newline_bytes_re_pattern = '{backslash}|{doublequote}|{newline}|{not_valid_literal_ascii}'.format(**pattern_dict).encode('ascii')
        self._invalid_literal_or_backslash_doublequote_newline_bytes_re = re.compile(invalid_literal_or_backslash_doublequote_newline_bytes_re_pattern)

        invalid_literal_or_backslash_singlequote_bytes_re_pattern = '{backslash}|{singlequote}|{not_valid_literal_ascii}'.format(**pattern_dict).encode('ascii')
        self._invalid_literal_or_backslash_singlequote_bytes_re = re.compile(invalid_literal_or_backslash_singlequote_bytes_re_pattern)
        invalid_literal_or_backslash_doublequote_bytes_re_pattern = '{backslash}|{doublequote}|{not_valid_literal_ascii}'.format(**pattern_dict).encode('ascii')
        self._invalid_literal_or_backslash_doublequote_bytes_re = re.compile(invalid_literal_or_backslash_doublequote_bytes_re_pattern)


    @staticmethod
    def _escape_unicode_char_xubrace(c, ord=ord):
        '''
        Escape a Unicode code point using `\\xHH` (8-bit) or
        `\\u{H....H}` notation.
        '''
        n = ord(c)
        if n < 256:
            return '\\x{0:02x}'.format(n)
        return '\\u{{{0:0x}}}'.format(n)


    @staticmethod
    def _escape_unicode_char_xuU(c, ord=ord):
        '''
        Escape a Unicode code point using `\\xHH` (8-bit), `\\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (24-bit) notation.
        '''
        n = ord(c)
        if n < 256:
            return '\\x{0:02x}'.format(n)
        elif n < 65536:
            return '\\u{0:04x}'.format(n)
        return '\\U{0:08x}'.format(n)


    @staticmethod
    def _escape_unicode_char_ubrace(c, ord=ord):
        '''
        Escape a Unicode code point using `\\u{H....H}` notation.
        '''
        return '\\u{{{0:0x}}}'.format(ord(c))


    @staticmethod
    def _escape_unicode_char_uU(c, ord=ord):
        '''
        Escape a Unicode code point using \\uHHHH` (16-bit),
        or `\\UHHHHHHHH` (24-bit) notation.
        '''
        n = ord(c)
        if n < 65536:
            return '\\u{0:04x}'.format(n)
        return '\\U{0:08x}'.format(n)


    def escape_unicode(self, s, delim, all=False, inline=False):
        '''
        Within a string, replace all code points that are not allowed to
        appear literally with their escaped counterparts.
        '''
        if delim != "'" and delim != '"':
            raise TypeError
        d = self._escape_unicode_dict
        if all:
            v = ''.join(d[c] for c in s)
        else:
            if inline:
                if delim == "'":
                    r = self._invalid_literal_or_backslash_singlequote_newline_unicode_re
                else:
                    r = self._invalid_literal_or_backslash_doublequote_newline_unicode_re
            else:
                if delim == "'":
                    r = self._invalid_literal_or_backslash_singlequote_unicode_re
                else:
                    r = self._invalid_literal_or_backslash_doublequote_unicode_re
            v = r.sub(lambda m: d[m.group(0)], s)
        return v


    def escape_bytes(self, b, delim, inline=False):
        '''
        Within a binary string, replace all bytes whose corresponding Latin-1
        code points are not allowed to appear literally with their escaped
        counterparts.
        '''
        if delim != "'" and delim != '"':
            raise TypeError
        d = self._escape_bytes_dict
        if inline:
            if delim == "'":
                r = self._invalid_literal_or_backslash_singlequote_newline_bytes_re
            else:
                r = self._invalid_literal_or_backslash_doublequote_newline_bytes_re
        else:
            if delim == "'":
                r = self._invalid_literal_or_backslash_singlequote_bytes_re
            else:
                r = self._invalid_literal_or_backslash_doublequote_bytes_re
        return r.sub(lambda m: d[m.group(0)], b)




class Unescape(object):
    '''
    Replace escaped code points and bytes in Unicode strings and byte strings
    with their unescaped equivalents.
    '''
    def __init__(self):
        # Dicts for unescaping start with all short escapes; factory
        # functions generate additional escapes as requested.  The bytes dict
        # is largely prepopulated, but can't be fully prepopulated because
        # of `\<spaces><newline>` escapes.
        self._unescape_unicode_dict = tooling.keydefaultdict(self._unescape_unicode_char, grammar.SHORT_BACKSLASH_UNESCAPES)
        self._unescape_bytes_dict = tooling.keydefaultdict(self._unescape_byte)
        self._unescape_bytes_dict.update({'\\x{0:02x}'.format(n).encode('ascii'): chr(n).encode('latin1') for n in range(256)})
        self._unescape_bytes_dict.update(grammar.SHORT_BACKSLASH_UNESCAPES)

        # Regexes for finding escaped code points and bytes
        unescape_unicode = grammar.RE_GRAMMAR['unicode_escape']
        unescape_bytes = grammar.RE_GRAMMAR['bytes_escape']
        newline = NEWLINE
        self._unescape_unicode_re = re.compile(unescape_unicode)
        self._unescape_unicode_or_replace_newline_re = re.compile('{0}|{1}'.format(newline, unescape_unicode))
        self._unescape_bytes_re = re.compile(unescape_bytes.encode('ascii'))
        self._unescape_bytes_or_replace_newline_re = re.compile('{0}|{1}'.format(newline, unescape_bytes).encode('ascii'))


    @staticmethod
    def _unescape_unicode_char(s, int=int, chr=chr, newline=NEWLINE):
        '''
        Given a string in `\\xHH`, `\\u{H....H}`, `\\uHHHH`, or `\\UHHHHHHHH`
        form, return the Unicode code point corresponding to the hex value of
        the `H`'s.  Given `\\<spaces><newline>`, return an empty string.
        Otherwise, raise an error for `\\<char>` or `\\`, which is the only
        other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the
        allowed forms.  Before this function is invoked, all known short
        (2-letter) escape sequences and any newline replacements have already
        been filtered out.  Any remaining short escapes `\\<char>` at this
        point are unrecognized.
        '''
        try:
            v = chr(int(s[2:].strip('{}'), 16))
        except ValueError:
            # Check for the pattern `\\<spaces><newline>`.
            # Given regex, no need to worry about multiple newlines.
            if s[-1] == newline:
                v = ''
            else:
                if 0x21 <= ord(s[-1]) <= 0x7E:
                    s_esc = s
                else:
                    s_esc = '\\<U+{0:0x}>'.format(ord(s[-1]))
                raise erring.UnknownEscapeError(s, s_esc)
        return v


    @staticmethod
    def _unescape_byte(b, int=int, chr=chr, newline=NEWLINE.encode('latin1')):
        '''
        Given a binary string in `\\xHH` form, return the byte corresponding
        to the hex value of the `H`'s.  Given `\\<spaces><newline>`, return
        an empty byte string.  Otherwise, raise an error for `\\<byte>` or
        `\\`, which is the only other form the argument will ever take.

        Arguments to this function are prefiltered by a regex into the allowed
        hex escape forms.  Before this function is invoked, all known short
        (2-letter) escape sequences and any newline replacements have already
        been filtered out.  Any remaining short escapes `\\<byte>` at this
        point are unrecognized.
        '''
        try:
            v = chr(int(b[2:], 16)).encode('latin1')
        except ValueError:
            # Make sure we have the full pattern `\\<spaces><newline>`
            if b[-1] == newline:
                v = b''
            else:
                b_esc = b.decode('latin1')
                if not 0x21 <= ord(b_esc[-1]) <= 0x7E:
                    b_esc = '\\<0x{0:02x}>'.format(ord(b_esc[-1]))
                raise erring.UnknownEscapeError(b, b_esc)
        return v


    def unescape_unicode(self, s, newline=None, _default_newline=NEWLINE):
        '''
        Within a string, replace all backslash escapes with the
        corresponding code points.
        '''
        d = self._unescape_unicode_dict
        if newline is None or newline == _default_newline:
            return self._unescape_unicode_re.sub(lambda m: d[m.group(0)], s)
        else:
            d[_default_newline] = newline
            return self._unescape_unicode_or_replace_newline_re.sub(lambda m: d[m.group(0)], s)


    def unescape_bytes(self, b, newline=None, _default_newline=NEWLINE.encode('latin1')):
        '''
        Within a binary string, replace all backslash escapes with the
        corresponding bytes.
        '''
        d = self._unescape_bytes_dict
        if newline is None or newline == _default_newline:
            return self._unescape_bytes_re.sub(lambda m: d[m.group(0)], b)
        else:
            d[_default_newline] = newline
            return self._unescape_bytes_or_replace_newline_re.sub(lambda m: d[m.group(0)], b)