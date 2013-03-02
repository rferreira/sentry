import logging, tempfile, zipfile, csv, StringIO, os.path
import time, prettytable, threading

from Queue import Queue

import requests
import dns.query

from sentry import counter

log = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 30.0 # 30 seconds query timeout

class SentryBenchmark(object):
    """
    Fairly repeatable benchmark using Alexa's TOP 1M sites
    """

    ALEXA_URL = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
    FILENAME = 'top-1m.csv'

    def __init__(self, server, workers, limit):
        log.info('starting benchmark')

        self.queue = Queue()

        self.server, self.port = server.split(':')
        self.limit = limit

        log.info('using %d workers' % workers)

        # build threadpool
        self.workers = [
            threading.Thread(target=self.worker) for i in range(workers)
        ]


    def start(self):

        # step 1 download alexas site list:
        path = os.path.join(tempfile.gettempdir(), 'alexas-cache')
        log.info('downloading Alexas sites from %s to %s so it can be reused later' % (self.ALEXA_URL,path))

        # seeing if the cache is still around
        if not os.path.exists(path):
            with open(path, 'wb') as fd:
                log.debug('writing file to %s ' % fd.name)
                r = requests.get(self.ALEXA_URL, stream=True)
                for chunk in iter(lambda: r.raw.read(1024),''):
                    fd.write(chunk)


            log.debug('downloading done')

        else:
            log.info('using local cache...')

        # loading all sites into dispatch queue
        entries = 0

        if self.limit >0:
            log.info('limiting run to %d entries' % self.limit)

        with open(path, 'r') as fd:
            zfd = zipfile.ZipFile(fd)
            data = StringIO.StringIO(zfd.read(self.FILENAME))
            reader = csv.reader(data)

            for row in reader:
                log.debug(row[1])
                self.queue.put(row[1])
                entries+=1

                if self.limit > 0 and entries >= self.limit:
                    log.info('limited reached, breaking')
                    break


        log.info('starting processing...')
        self.stats = counter.Counter()

        start_time = time.time()

        for thread in self.workers:
            thread.setDaemon(True)
            thread.start()

        log.info('%d domain names loaded'  % self.queue.qsize())
        log.info('test running')

        self.queue.join()

        log.info('benchmark done')
        self.stats.add('elapsed_time_seconds', int(time.time() - start_time) )

        # dumping results:
        x = prettytable.PrettyTable(['metric', 'value'])
        x.align = 'l'

        for r in self.stats.get_metrics():
            x.add_row([r['name'], r['value']])

        log.info('results: \n' + str(x) )


        return


    def worker(self):
        log.debug('worker started')
        while True:
            item = self.queue.get()

            try:
                log.debug('resolving %s' % item )

                self.stats.inc_ops('queries')

                start_time = time.time()
                message = dns.message.make_query(item, 'A')
                response = dns.query.udp(message, self.server, port=int(self.port),timeout=DEFAULT_TIMEOUT)
                log.debug(response.answer)

                self.stats.add_avg('response_time_msec', (time.time() - start_time)*1000 )
                self.stats.dec_ops('queries')

            except Exception as e:
                self.stats.inc_ops('queries_failed')
                log.exception(e)

            finally:
                self.queue.task_done()

