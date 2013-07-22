import logging, tempfile, zipfile, csv, StringIO, os.path
import time, prettytable, threading

from Queue import Queue

import futures
import requests
import dns.query, dns.reversename, dns.exception

from sentry import counter

log = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 1.0 # 1 seconds query timeout


class SentryBenchmark(object):
    """
    Fairly repeatable benchmark using Alexa's TOP 1M sites
    """

    ALEXA_URL = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
    FILENAME = 'top-1m.csv'

    def __init__(self, server, workers, limit):
        log.info('starting benchmark')


        self.server, self.port = server.split(':')
        self.limit = limit

        log.info('using %d workers' % workers)

        # sanity checking the server name:
        try:
            dns.reversename.from_address(self.server)
        except dns.exception.SyntaxError:
            raise Exception('server name must be an ip not DNS name, you gave us: %s' % self.server)

        log.info('benchmarking host: %s port: %s' % (self.server, self.port))

        # build threadpool
        self.executor = futures.ThreadPoolExecutor(max_workers=workers)


    def start(self):

        # step 1 download alexas site list:
        path = os.path.join(tempfile.gettempdir(), 'alexas-cache')

        # seeing if the cache is still around
        if not os.path.exists(path):
            with open(path, 'wb') as fd:
                log.info('downloading Alexas sites from %s to %s so it can be reused later' % (self.ALEXA_URL,path))
                r = requests.get(self.ALEXA_URL, stream=True)
                for chunk in iter(lambda: r.raw.read(1024),''):
                    fd.write(chunk)


            log.debug('downloading done')

        else:
            log.info('using local cache...')

        # loading all sites into dispatch queue
        processed_queries = 0

        if self.limit >0:
            log.info('limiting run to %d entries' % self.limit)


        log.info('starting processing...')
        self.stats = counter.Counter()

        processed_entries = 0

        start_time = time.time()


        with open(path, 'r') as fd:
            zfd = zipfile.ZipFile(fd)
            data = StringIO.StringIO(zfd.read(self.FILENAME))
            reader = csv.reader(data)

            for row in reader:
                if self.limit > 0 and processed_entries == self.limit:
                    log.info('limited reached, breaking')
                    break

                item = row[1]

                # performing query:
                log.debug('resolving %s' % item )

                try:
                    response_start_time = time.time()
                    message = dns.message.make_query(item, 'A')
                    response = dns.query.udp(message, self.server, port=int(self.port),timeout=DEFAULT_TIMEOUT)
                    log.debug(response.answer)

                    assert len(response.answer) >0

                    response_elapsed_time = (time.time() - response_start_time)*1000

                    log.debug('query in %d msec' % response_elapsed_time)
                    self.stats.add_avg('response_time_msec', response_elapsed_time  )
                    self.stats.add('queries_successful')

                except Exception as e:
                    log.exception(e)
                    self.stats.add('queries_failed')

                finally:
                    processed_entries +=1


        log.info('benchmark done')
        elapsed_time_seconds = int(time.time() - start_time)
        elapsed_time_seconds = elapsed_time_seconds if elapsed_time_seconds > 0 else 1
        self.stats.add('elapsed_time_seconds', elapsed_time_seconds )
        self.stats.add('queries_per_second', int(processed_entries/elapsed_time_seconds) )

        # dumping results:
        x = prettytable.PrettyTable(['metric', 'value'])
        x.align = 'l'

        for r in self.stats.get_metrics():
            x.add_row([r['name'], r['value']])

        log.info('results: \n' + str(x) )

