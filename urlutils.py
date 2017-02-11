import urllib

import sublime
import sublime_plugin
import urllib.request
from urllib.parse import urlparse, parse_qsl


def selections(view):
    # get selected text regions or all text region if none selected
    regions = [r for r in view.sel() if not r.empty()]

    if not regions:
        regions = [sublime.Region(0, view.size())]

    return regions


class ReplaceCommand(sublime_plugin.TextCommand):
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
            view.replace(edit, region, processed_str + '\n')


class UrlencodeCommand(ReplaceCommand):
    process = staticmethod(lambda s: urllib.parse.quote(s, safe='\r\n'))


class UrldecodeCommand(ReplaceCommand):
    process = staticmethod(lambda s: urllib.parse.unquote(s.replace('+', ' ')))


class UrlparseCommand(ReplaceCommand):
    @staticmethod
    def _query_parse(val):
        lines = []
        query = dict(parse_qsl(val))
        max_key_len = max(map(len, query.keys())) + 3
        for k, v in sorted(query.items()):
            lines.append('{key} : {val}'.format(key=k.rjust(max_key_len, ' '), val=v))
        return lines

    @staticmethod
    def process(s):
        parsed = urlparse(s)

        lines = []
        for f in ['scheme', 'netloc', 'path', 'params', 'query', 'fragment']:
            # skip empty vals
            val = getattr(parsed, f)
            if not val:
                continue

            # header
            lines.append('\n' + (' ' + f + ' ').center(75, '-') + '\n')

            # key-vals
            if f == 'query':
                lines.extend(UrlparseCommand._query_parse(val))
            else:
                lines.append(val)

        lines = [UrldecodeCommand.process(x) for x in lines]
        return '\n'.join(lines).strip()


class UrlresponseCommand(ReplaceCommand):
    @staticmethod
    def process(s):
        with urllib.request.urlopen(s) as response:
            resp = response.read()
        return resp.decode('utf8')
