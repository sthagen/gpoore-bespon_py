# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, Geoffrey M. Poore
# All rights reserved.
#
# Licensed under the BSD 3-Clause License:
# http://opensource.org/licenses/BSD-3-Clause
#


# pylint: disable=C0301, C0330

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import re
from . import re_patterns




# General notes on suffixes in variable names.  Note that these suffixes only
# have the meanings described below when used as suffixes.
#  * Use of "ascii" suffix in a variable name indicates a restriction to code
#    points in 0x00-0x7F, or 0-127 (that is, 7-bit).
#  * Use of "below_u0590" suffix in a variable name indicates a restriction
#    to code points below 0x590, which is a convenient range because it
#    contains very few invalid code points (only those in Unicode Cc) and
#    does not contain any right-to-left code points.  Thus, regex patterns
#    are only marginally more complex and slower than for the ASCII range,
#    while rtl checks may be omitted.
#  * Use of "unicode" suffix in a variable name indicates that the full range
#    of Unicode code points in 0x00-0x10FFFF is covered.


# Assemble literal grammar
_RAW_LIT_GRAMMAR = [# Whitespace
                    ('tab', '\t'),
                    ('space', '\x20'),
                    ('indent', '{tab}{space}'),
                    ('newline', '\n'),
                    ('line_terminator_ascii', '\n\v\f\r'),
                    ('line_terminator_unicode', '{line_terminator_ascii}\u0085\u2028\u2029'),
                    ('whitespace', '{indent}{newline}'),
                    # unicode_whitespace = set([cp for cp, data in unicodetools.ucd.proplist.items() if 'White_Space' in data])
                    ('unicode_whitespace', ('\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680' +
                                            '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a' +
                                            '\u2028\u2029\u202f\u205f\u3000')),
                    # Other
                    ('bom', '\uFEFF')]

_RAW_LIT_SPECIAL = [# Special code points
                    ('comment_delim', '#'),
                    ('assign_key_val', '='),
                    ('open_noninline_list', '*'),
                    ('start_inline_dict', '{'),
                    ('end_inline_dict', '}'),
                    ('start_inline_list', '['),
                    ('end_inline_list', ']'),
                    ('start_tag', '('),
                    ('end_tag', ')'),
                    ('end_tag_suffix', '>'),
                    ('inline_element_separator', ','),
                    ('block_prefix', '|'),
                    ('block_suffix', '/'),
                    ('escaped_string_singlequote_delim', "'"),
                    ('escaped_string_doublequote_delim', '"'),
                    ('literal_string_delim', '`'),
                    ('path_separator', '.'),
                    ('alias_prefix', '$'),
                    ('home_alias', '~'),
                    ('self_alias', '_'),
                    # Combinations
                    ('end_tag_with_suffix', '{end_tag}{end_tag_suffix}'),
                    # Tokens that are invalid when encountered after certain
                    # other tokens.  The logic here is a little subtle.  Doc
                    # comments and tags are parsed and then stored until being
                    # used, unlike other objects that are immediately added to
                    # the AST.  Whenever a scalar or collection object is
                    # added to the AST, any stored doc comment and tag are
                    # applied to it.  Because doc comments and tags are
                    # stored, there is a danger of a stored object never being
                    # used.
                    #
                    # One way to deal with this would be to have a check at
                    # the relevant tokens for an unused doc comment or tag.
                    # Another option, which is implemented, is to look ahead
                    # after doc comments and tags to check for a valid
                    # following token.  During the lookahead, all following
                    # whitespace and line comments (as opposed to doc
                    # comments) are discarded.  The next token after this
                    # procedure is then checked against a set of invalid
                    # tokens.  The invalid tokens are those that would either
                    # close an object (as opposed to opening it, so that the
                    # stored doc comment or tag would be used), or start an
                    # object that is invalid in the current context (a second
                    # doc comment or tag).  Blocks are a special case
                    # requiring additional lookahead, to determine their type.
                    # Any other token will either start a valid object, or
                    # will be a universally invalid token that triggers its
                    # own error.  Note that there is an exception for dicts in
                    # non-inline syntax, since two doc comment/tag pairs can
                    # follow each other sequentially, with the first being
                    # applied to the dict and the second applying to the first
                    # key.
                    ('doc_comment_invalid_next_token', '{block_prefix}{comment_delim}{assign_key_val}{end_inline_dict}{end_inline_list}{end_tag}{inline_element_separator}'),
                    ('tag_invalid_next_token', '{comment_delim}{assign_key_val}{end_inline_dict}{end_inline_list}{end_tag}{inline_element_separator}'),
                    # Numbers
                    ('number_or_number_unit_start', '0123456789+-')]
_RAW_LIT_GRAMMAR.extend(_RAW_LIT_SPECIAL)

LIT_GRAMMAR = {}
for k, v in _RAW_LIT_GRAMMAR:
    if k in ('start_inline_dict', 'end_inline_dict'):
        LIT_GRAMMAR[k] = v
    else:
        LIT_GRAMMAR[k] = v.format(**LIT_GRAMMAR)
# Add a few elements that couldn't conveniently be created with the grammar
# definition format
LIT_GRAMMAR['line_terminator_ascii_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['line_terminator_ascii'])
LIT_GRAMMAR['line_terminator_unicode_seq'] = ('\r\n',) + tuple(x for x in LIT_GRAMMAR['line_terminator_unicode'])




# Assemble regex grammar
_RAW_RE_GRAMMAR = [('backslash', '\\\\')]

# Regex patterns
_RE_PATTERNS = [('xid_start_ascii', re_patterns.XID_START_ASCII),
                ('xid_start_below_u0590', re_patterns.XID_START_BELOW_U0590),
                ('xid_start_less_fillers', re_patterns.XID_START_LESS_FILLERS),
                ('xid_continue_ascii', re_patterns.XID_CONTINUE_ASCII),
                ('xid_continue_below_u0590', re_patterns.XID_CONTINUE_BELOW_U0590),
                ('xid_continue_less_fillers', re_patterns.XID_CONTINUE_LESS_FILLERS),
                ('not_valid_ascii', re_patterns.NOT_VALID_LITERAL_ASCII),
                ('not_valid_below_u0590', re_patterns.NOT_VALID_LITERAL_BELOW_U0590),
                ('not_valid_unicode', re_patterns.NOT_VALID_LITERAL),
                ('bidi_rtl', re_patterns.BIDI_R_AL),
                ('private_use', re_patterns.PRIVATE_USE)]
_RAW_RE_GRAMMAR.extend(_RE_PATTERNS)

# Whitespace
_RAW_RE_WS = [('space', re.escape(LIT_GRAMMAR['space'])),
              ('indent', '[{0}]'.format(re.escape(LIT_GRAMMAR['indent']))),
              ('newline', re.escape(LIT_GRAMMAR['newline'])),
              ('whitespace', '[{0}]'.format(re.escape(LIT_GRAMMAR['whitespace'])))]
_RAW_RE_GRAMMAR.extend(_RAW_RE_WS)

# Special characters
for k, v in _RAW_LIT_SPECIAL:
    _RAW_RE_GRAMMAR.append((k, re.escape(LIT_GRAMMAR[k])))

# Types
_RAW_RE_TYPE = [# None type
                ('none_type', 'none'),
                ('none_type_invalid_word', '[nN][oO][nN][eE]'),

                # Boolean
                ('bool_true', 'true'),
                ('bool_false', 'false'),
                ('bool_invalid_word', '[tT][rR][uU][eE]|[fF][aA][lL][sS][eE]'),

                # Basic numeric elements
                ('sign', '[+-]'),
                ('opt_sign_indent', '(?:{sign}{indent}*)?'),
                ('zero', '0'),
                ('nonzero_dec_digit', '[1-9]'),
                ('dec_digit', '[0-9]'),
                ('dec_digits_underscores', '{dec_digit}+(?:_{dec_digit}+)*'),
                ('lower_hex_digit', '[0-9a-f]'),
                ('lower_hex_digits_underscores', '{lower_hex_digit}+(?:_{lower_hex_digit}+)*'),
                ('upper_hex_digit', '[0-9A-F]'),
                ('upper_hex_digits_underscores', '{upper_hex_digit}+(?:_{upper_hex_digit}+)*'),
                ('oct_digit', '[0-7]'),
                ('oct_digits_underscores', '{oct_digit}+(?:_{oct_digit}+)*'),
                ('bin_digit', '[01]'),
                ('bin_digits_underscores', '{bin_digit}+(?:_{bin_digit}+)*'),

                # Number types
                # Integers
                ('dec_integer', '{opt_sign_indent}(?:{zero}|{nonzero_dec_digit}{dec_digit}*(?:_{dec_digit}+)*)'),
                ('hex_integer', '{opt_sign_indent}0x_?(?:{lower_hex_digits_underscores}|{upper_hex_digits_underscores})'),
                ('oct_integer', '{opt_sign_indent}0o_?{oct_digits_underscores}'),
                ('bin_integer', '{opt_sign_indent}0b_?{bin_digits_underscores}'),
                ('integer', '{dec_integer}|{hex_integer}|{oct_integer}|{bin_integer}'),
                # Floats
                ('dec_exponent', '[eE]{sign}?{dec_digits_underscores}'),
                ('decimal_point', '\\.'),
                ('dec_float', '''
                              {opt_sign_indent}(?:{zero}|{nonzero_dec_digit}{dec_digit}*(?:_{dec_digit}+)*)
                                  (?:{decimal_point}{dec_digits_underscores}(?:_?{dec_exponent})?|_?{dec_exponent})
                              '''.replace('\x20', '').replace('\n', '')),
                ('hex_exponent', '[pP]{sign}?{dec_digits_underscores}'),
                ('hex_float', '''
                              {opt_sign_indent}0x_?
                              (?:{lower_hex_digits_underscores}(?:{decimal_point}{lower_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent}) |
                                 {upper_hex_digits_underscores}(?:{decimal_point}{upper_hex_digits_underscores}(?:_?{hex_exponent})? | _?{hex_exponent})
                              )
                              '''.replace('\x20', '').replace('\n', '')),
                ('infinity', '{opt_sign_indent}inf'),
                ('not_a_number', '{opt_sign_indent}nan'),
                ('float_invalid_word', '{opt_sign_indent}(?:[iI][nN][fF]|[nN][aA][nN])'),
                ('float', '{dec_float}|{hex_float}|{infinity}|{not_a_number}'),

                # Unquoted strings
                ('unquoted_start_ascii', '{xid_start_ascii}'),
                ('unquoted_start_below_u0590', '{xid_start_below_u0590}'),
                ('unquoted_start_unicode', '{xid_start_less_fillers}'),
                ('unquoted_continue_ascii', '{xid_continue_ascii}'),
                ('unquoted_continue_below_u0590', '{xid_continue_below_u0590}'),
                ('unquoted_continue_unicode', '{xid_continue_less_fillers}'),
                ('unquoted_key_ascii', '_*{unquoted_start_ascii}{unquoted_continue_ascii}*'),
                ('unquoted_key_below_u0590', '_*{unquoted_start_below_u0590}{unquoted_continue_below_u0590}*'),
                ('unquoted_key_unicode', '_*{unquoted_start_unicode}{unquoted_continue_unicode}*'),
                ('unquoted_string_ascii', '{unquoted_key_ascii}(?:{space}{unquoted_continue_ascii}+)+'),
                ('unquoted_string_below_u0590', '{unquoted_key_below_u0590}(?:{space}{unquoted_continue_below_u0590}+)+'),
                ('unquoted_string_unicode', '{unquoted_key_unicode}(?:{space}{unquoted_continue_unicode}+)+'),
                ('si_mu_prefix', '(?:\u00B5|\u03BC)'),
                ('unquoted_unit_ascii', '''
                                        (?: [A-NP-WY-Za-km-wy-z][A-Za-z]+ |
                                            [Xx][G-Zg-z][A-Za-z]* |
                                            [AC-DF-HJ-NP-WY-Zac-df-hj-km-np-rw-z] |
                                            %
                                        )
                                        '''.replace('\x20', '').replace('\n', '')),
                ('unquoted_dec_number_unit_ascii', '(?:{dec_integer}|{dec_float}){unquoted_unit_ascii}'),
                ('unquoted_dec_number_unit_below_u0590', '(?:{dec_integer}|{dec_float}){si_mu_prefix}?{unquoted_unit_ascii}'),
                ('unquoted_dec_number_unit_unicode', '{unquoted_dec_number_unit_below_u0590}'),

                # Key path
                ('key_path_element_ascii', '(?:{unquoted_key_ascii}|{open_noninline_list})'),
                ('key_path_element_below_u0590', '(?:{unquoted_key_below_u0590}|{open_noninline_list})'),
                ('key_path_element_unicode', '(?:{unquoted_key_unicode}|{open_noninline_list})'),
                ('key_path_ascii', '{key_path_element_ascii}(?:{path_separator}{key_path_element_ascii})+'),
                ('key_path_below_u0590', '{key_path_element_below_u0590}(?:{path_separator}{key_path_element_below_u0590})+'),
                ('key_path_unicode', '{key_path_element_unicode}(?:{path_separator}{key_path_element_unicode})+'),

                # Alias path
                ('alias_path_ascii', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_key_ascii})(?:{path_separator}{unquoted_key_ascii})+'),
                ('alias_path_below_u0590', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_key_below_u0590})(?:{path_separator}{unquoted_key_below_u0590})+'),
                ('alias_path_unicode', '{alias_prefix}(?:{home_alias}|{self_alias}|{unquoted_key_unicode})(?:{path_separator}{unquoted_key_unicode})+'),

                # Binary types
                ('base16', '{lower_hex_digit}+|{upper_hex_digit}+'),
                ('base64', '[A-Za-z0-9+/=]+')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_TYPE)

# Escapes (no string formatting is performed on these, so braces are fine)
_RAW_RE_ESC = [('x_escape', '\\\\x(?:{lower_hex_digit}{{2}}|{upper_hex_digit}{{2}})'),
               ('u_escape', '\\\\u(?:{lower_hex_digit}{{4}}|{upper_hex_digit}{{4}})'),
               ('U_escape', '\\\\U(?:{lower_hex_digit}{{8}}|{upper_hex_digit}{{8}})'),
               ('ubrace_escape', '\\\\u\\{{(?:{lower_hex_digit}{{1,6}}|{upper_hex_digit}{{1,6}})\\}}'),
               # The general escape patterns can include `\<spaces><newline>`,
               # but don't need to be compiled with re.DOTALL because the
               # newlines are specified explicitly and accounted for before
               # the dot in the patterns.  The last two patterns (arbitrary
               # character after backslash, or none) don't lead to errors,
               # because all such matches are filtered through a dict of
               # valid short escapes.  Invalid escapes are caught at that
               # point; the regex pattern just needs to catch everything that
               # could be a valid escape.
               ('bytes_escape', '{x_escape}|\\\\{space}*{newline}|\\\\.|\\\\'),
               ('unicode_escape', '{x_escape}|{u_escape}|{U_escape}|{ubrace_escape}|\\\\{space}*{newline}|\\\\.|\\\\')]
_RAW_RE_GRAMMAR.extend(_RAW_RE_ESC)

_raw_key_not_formatted = set(k for k, v in _RAW_LIT_SPECIAL) | set(k for k, v in _RE_PATTERNS)

RE_GRAMMAR = {}
for k, v in _RAW_RE_GRAMMAR:
    if k in _raw_key_not_formatted:
        RE_GRAMMAR[k] = v
    else:
        RE_GRAMMAR[k] = v.format(**RE_GRAMMAR)




# Other grammar-related elements

# Default short backslash escapes.
SHORT_BACKSLASH_UNESCAPES = {'\\\\': '\\',
                             "\\'": "'",
                             '\\"': '"',
                             '\\a': '\a',
                             '\\b': '\b',
                             '\\e': '\x1B',
                             '\\f': '\f',
                             '\\n': '\n',
                             '\\r': '\r',
                             '\\t': '\t',
                             '\\v': '\v'}

SHORT_BACKSLASH_ESCAPES = {v: k for k, v in SHORT_BACKSLASH_UNESCAPES.items()}


# Non-textual parameters
PARAMS = {'max_delim_length': 3*30}