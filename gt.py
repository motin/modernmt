import random
import sys
import threading
import time
from multiprocessing.dummy import Pool
from queue import Queue

import requests

from cli.mmt.processing import XMLEncoder


class TranslateError(Exception):
    def __init__(self, message) -> None:
        super().__init__()
        self.message = message

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.message)

    def __str__(self):
        return self.message


class TranslateEngine(object):
    def __init__(self, source_lang, target_lang):
        self.source_lang = source_lang
        self.target_lang = target_lang

    @property
    def name(self):
        raise NotImplementedError

    def _get_default_threads(self):
        raise NotImplementedError

    def translate_text(self, text):
        raise NotImplementedError

    def translate_batch(self, generator, consumer, threads=None, suppress_errors=False):
        pool = Pool(threads if threads is not None else self._get_default_threads())
        jobs = Queue()

        raise_error = []

        def _consumer_thread_run():
            while True:
                job = jobs.get(block=True)

                if job is None:
                    break

                try:
                    translation = job.get()
                    consumer(translation)
                except Exception as e:
                    raise_error.append(e)
                    break

        consumer_thread = threading.Thread(target=_consumer_thread_run)
        consumer_thread.start()

        def _translate_text(text):
            try:
                return self.translate_text(text)
            except BaseException as e:
                if suppress_errors:
                    print(str(e), file=sys.stderr)
                    return ''
                else:
                    raise

        try:
            count = 0
            for line in generator:
                count += 1
                _job = pool.apply_async(_translate_text, (line,))
                jobs.put(_job, block=True)
            return count
        finally:
            jobs.put(None, block=True)
            consumer_thread.join()
            pool.terminate()

            if len(raise_error) > 0:
                raise raise_error[0]

    def translate_stream(self, input_stream, output_stream, threads=None, suppress_errors=False):
        def generator():
            for line in input_stream:
                yield line.rstrip('\n')

        def consumer(line):
            output_stream.write(line)
            output_stream.write('\n')

        return self.translate_batch(generator(), consumer, threads=threads, suppress_errors=suppress_errors)

    def translate_file(self, input_file, output_file, threads=None, suppress_errors=False):
        with open(input_file, 'r', encoding='utf-8') as input_stream:
            with open(output_file, 'w', encoding='utf-8') as output_stream:
                return self.translate_stream(input_stream, output_stream,
                                             threads=threads, suppress_errors=suppress_errors)


class EchoTranslate(TranslateEngine):
    def __init__(self, source_lang, target_lang):
        super().__init__(source_lang, target_lang)

    @property
    def name(self):
        return 'Echo Translate'

    def _get_default_threads(self):
        return 16

    def translate_text(self, text):
        return text


class GoogleRateLimitError(TranslateError):
    def __init__(self, message) -> None:
        super().__init__(message)


class GoogleServerError(TranslateError):
    def __init__(self, *args, **kwargs):
        super(GoogleServerError, self).__init__(*args, **kwargs)


class GoogleTranslate(TranslateEngine):
    DEFAULT_GOOGLE_KEY = 'AIzaSyBl9WAoivTkEfRdBBSCs4CruwnGL_aV74c'

    def __init__(self, source_lang, target_lang, key=None):
        TranslateEngine.__init__(self, source_lang, target_lang)
        self._key = key if key is not None else self.DEFAULT_GOOGLE_KEY
        self._delay = 0
        self._url = 'https://translation.googleapis.com/language/translate/v2'

    @property
    def name(self):
        return 'Google Translate'

    def _get_default_threads(self):
        return 5

    @staticmethod
    def _normalize_language(lang):
        fields = lang.split('-')
        if fields[0] == "zh" and len(fields) > 1:
            if fields[1] == "CN" or fields[1] == "TW":
                return lang
        return fields[0]

    @staticmethod
    def _pack_error(request):
        json = request.json()

        if request.status_code == 403:
            for error in json['error']['errors']:
                if error['reason'] == 'dailyLimitExceeded':
                    return TranslateError('Google Translate free quota is over. Please use option --gt-key'
                                          ' to specify your GT API key.')
                elif error['reason'] == 'userRateLimitExceeded':
                    print("Google Translate rate limit exceeded")
                    return GoogleRateLimitError('Google Translate rate limit exceeded')
        elif 500 <= request.status_code < 600:
            return GoogleServerError('Google Translate server error (%d): %s' %
                                     (request.status_code, json['error']['message']))

        # hack around "API key expired. Please renew the API key." bug for newly created api keys
        if request.status_code == 400 and json['error']['message'] == "API key expired. Please renew the API key":
            print("HACK around 400...")
            time.sleep(1.)
            return GoogleRateLimitError('Google Translate rate limit exceeded')

        return TranslateError('Google Translate error (%d): %s' % (request.status_code, json['error']['message']))

    def _increment_delay(self):
        if self._delay < 0.002:
            self._delay = 0.05
        else:
            self._delay = min(1, self._delay * 1.05)

    def _decrement_delay(self):
        self._delay *= 0.95

        if self._delay < 0.002:
            self._delay = 0

    def translate_text(self, text):
        text_has_xml = XMLEncoder.has_xml_tag(text)

        if not text_has_xml:
            text = XMLEncoder.unescape(text)

        data = {
            'model': 'nmt',
            'source': self._normalize_language(self.source_lang),
            'target': self._normalize_language(self.target_lang),
            'q': text,
            'key': self._key,
            'userip': '.'.join(map(str, (random.randint(0, 200) for _ in range(4))))
        }

        headers = {
            'X-HTTP-Method-Override': 'GET'
        }

        rate_limit_reached = False
        server_error_count = 0

        while True:
            if self._delay > 0:
                delay = self._delay * random.uniform(0.5, 1)
                time.sleep(delay)

            r = requests.post(self._url, data=data, headers=headers)
            print("r", r)

            if r.status_code != requests.codes.ok:
                e = self._pack_error(r)
                if isinstance(e, GoogleRateLimitError):
                    rate_limit_reached = True
                    self._increment_delay()
                elif isinstance(e, GoogleServerError):
                    server_error_count += 1

                    if server_error_count < 10:
                        time.sleep(1.)
                    else:
                        raise e
                else:
                    raise e
            else:
                break

        if not rate_limit_reached and self._delay > 0:
            self._decrement_delay()

        translation = r.json()['data']['translations'][0]['translatedText']

        if not text_has_xml:
            translation = XMLEncoder.escape(translation)

        return translation

def parse_args(argv=None):
    import argparse
    from cli import CLIArgsException
    parser = argparse.ArgumentParser(description='Evaluate a ModernMT engine', prog='mmt evaluate')
    parser.add_argument('-s', '--source', dest='src_lang', metavar='SOURCE_LANGUAGE', default=None,
                        help='the source language (ISO 639-1). Can be omitted if engine is monolingual.')
    parser.add_argument('-t', '--target', dest='tgt_lang', metavar='TARGET_LANGUAGE', default=None,
                        help='the target language (ISO 639-1). Can be omitted if engine is monolingual.')
    parser.add_argument('--input', dest='input_file', metavar='INPUT', default=None,
                        help='the path to the test corpora')
    parser.add_argument('--output', dest='output_file', metavar='OUTPUT', default=None,
                        help='the path to output the translated corpora')

    parser.add_argument('--gt-key', dest='google_key', metavar='GT_API_KEY', default=None,
                        help='A custom Google Translate API Key to use for evaluating GT performance. '
                             'If not set, a default quota-limited key is used.'
                             'If set to "none", GT performance is not computed.')
    #parser.add_argument('--human-eval', dest='human_eval_path', metavar='OUTPUT', default=None,
    #                    help='the output folder for the tab-spaced files needed to setup a Human Evaluation benchmark')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='if debug is set, prevents temporary files to be removed after execution')

    args = parser.parse_args(argv)

    if args.src_lang is None or args.tgt_lang is None:
        raise CLIArgsException(parser,
                               'Missing language(s).')

    if args.input_file is None:
        raise CLIArgsException(parser,
                               'Missing input file.')

    if args.output_file is None:
        raise CLIArgsException(parser,
                               'Missing output file.')

    return args


def main(argv=None):
    args = parse_args(argv)

    gt = GoogleTranslate(args.src_lang, args.tgt_lang, key=args.google_key)

    import time
    try:
        begin_time = time.time()
        gt.translate_file(args.input_file, args.output_file)
        time = time.time() - begin_time
    except TranslateError as e:
        error = e
        raise error
    except Exception as e:
        error = TranslateError('Unexpected ERROR: ' + str(e))
        raise error

    print(f'Time: {time}')
    exit(0)


if __name__ == '__main__':
    main()
