import urllib

import sublime
import sublime_plugin
import urllib.request
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


def selections(view):
    # get selected text regions or all text region if none selected
    # from: https://github.com/mastahyeti/URLEncode/blob/master/urlencode.py#L24
    regions = [r for r in view.sel() if not r.empty()]

    if not regions:
        regions = [sublime.Region(0, view.size())]

    return regions


class ReplaceCommandBase(sublime_plugin.TextCommand):
    @staticmethod
    def process(s):
        raise Exception('`process` method is missing.')

    def run(self, edit):
        view = self.view
        drift = 0
        for region in selections(view):
            region.a += drift
            region.b += drift
            original_str = view.substr(region)
            processed_str = self.process(original_str)
            drift += len(processed_str) - len(original_str)
            view.replace(edit, region, processed_str)


class UrlencodeCommand(ReplaceCommandBase):
    process = staticmethod(lambda s: urllib.parse.quote(s, safe='\r\n'))


class UrldecodeCommand(ReplaceCommandBase):
    process = staticmethod(lambda s: urllib.parse.unquote(s.replace('+', ' ')))


class ParseCommandBase(ReplaceCommandBase):
    url_parts = ['scheme', 'netloc', 'path', 'params', 'query', 'fragment']

    def header_format(f):
        return '\n' + (' ' + f + ' ').center(75, '-') + '\n'


class UrlparseCommand(ParseCommandBase):

    @staticmethod
    def _query_parse(val):
        lines = []
        query = dict(parse_qsl(val))
        max_key_len = max(map(len, query.keys())) + 3
        for k, v in sorted(query.items()):
            lines.append('{key} : {val}'.format(key=k.rjust(max_key_len, ' '), val=v))
        return lines

    @staticmethod
    def _parse(s):
        parsed = urlparse(s)

        lines = []
        for f in ParseCommandBase.url_parts:
            # skip empty vals
            val = getattr(parsed, f)
            if not val:
                continue

            # header
            lines.append(ParseCommandBase.header_format(f))

            # key-vals
            if f == 'query':
                lines.extend(UrlparseCommand._query_parse(val))
            else:
                lines.append(val)

        lines = [UrldecodeCommand.process(x) for x in lines]
        return '\n'.join(lines).strip()

    @staticmethod
    def process(s):
        return UrlparseCommand._parse(s)


class UrlunparseCommand(ParseCommandBase):
    @staticmethod
    def _query_unparse(parsed_val):
        return urlencode(
            [(kv.split(' : ')[0].strip(), kv.split(' : ')[1])
             for kv in parsed_val.split('\n')]
        )

    @staticmethod
    def _unparse(s):
        found_parts = []
        found_values = [s]
        for url_part in ParseCommandBase.url_parts:
            header = ParseCommandBase.header_format(url_part).strip()
            if header in s:
                found_parts.append(url_part)
                found_values = found_values[0:-1] + found_values[-1].split(header)

        parsed_kv = dict(zip(found_parts, [val.strip('\n\r') for val in found_values[1:]]))
        parsed_kv['query'] = UrlunparseCommand._query_unparse(parsed_kv['query'])

        return urlunparse([parsed_kv.get(url_part, '')
                           for url_part in ParseCommandBase.url_parts])

    @staticmethod
    def process(s):
        return UrlunparseCommand._unparse(s)


class UrlresponseCommand(ReplaceCommandBase):
    @staticmethod
    def process(s):
        with urllib.request.urlopen(s) as response:
            resp = response.read()
        return resp.decode('utf8')
