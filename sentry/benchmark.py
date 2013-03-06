import logging, tempfile, zipfile, csv, StringIO, os.path
import time, prettytable, threading

from Queue import Queue

import futures
import requests
import dns.query

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
        entries = []

        if self.limit >0:
            log.info('limiting run to %d entries' % self.limit)

        with open(path, 'r') as fd:
            zfd = zipfile.ZipFile(fd)
            data = StringIO.StringIO(zfd.read(self.FILENAME))
            reader = csv.reader(data)

            for row in reader:
                log.debug(row[1])
                entries.append(row[1])

                if self.limit > 0 and len(entries) >= self.limit:
                    log.info('limited reached, breaking')
                    break


        status_thread = threading.Thread(target=self.status_worker)
        status_thread.setDaemon(True)
        status_thread.start()

        log.info('starting processing...')
        self.stats = counter.Counter()
        self.processed_entries = 0

        start_time = time.time()

        log.info('%d domain names loaded'  % len(entries))
        log.info('test running')

        fs = []
        for e in entries:
            fs.append(self.executor.submit(self.work_handler, e))

        for future in futures.as_completed(fs):
            try:
                log.debug('result %s' % future.result())
            except Exception as e:
                self.stats.add('queries_failed')
                log.exception(e)


        log.info('benchmark done')
        elapsed_time_seconds = int(time.time() - start_time)
        elapsed_time_seconds = elapsed_time_seconds if elapsed_time_seconds > 0 else 1
        self.stats.add('elapsed_time_seconds', elapsed_time_seconds )
        self.stats.add('queries_per_second', int(len(entries)/elapsed_time_seconds) )

        # dumping results:
        x = prettytable.PrettyTable(['metric', 'value'])
        x.align = 'l'

        for r in self.stats.get_metrics():
            x.add_row([r['name'], r['value']])

        log.info('results: \n' + str(x) )


        return

    def status_worker(self):
        while True:
            time.sleep(5)
            log.info('pending entries: %d' % (entries - self.processed_entries) )


    def work_handler(self, item):
        self.processed_entries += 1
        log.debug('resolving %s' % item )

        start_time = time.time()
        message = dns.message.make_query(item, 'A')
        response = dns.query.udp(message, self.server, port=int(self.port),timeout=DEFAULT_TIMEOUT)
        log.debug(response.answer)

        assert len(response.answer) >0

        self.stats.add_avg('response_time_msec', (time.time() - start_time)*1000 )
        self.stats.add('queries_successful')

        return response.answer



