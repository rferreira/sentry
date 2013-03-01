import requests
from Queue import Queue
import logging, tempfile, zipfile, csv, StringIO
import os.path
import threading

import dns.query

log = logging.getLogger(__name__)

class SentryBenchmark(object):
    ALEXA_URL = 'http://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
    FILENAME = 'top-1m.csv'

    def __init__(self, server, threadpool_size):
        log.info('starting benchmark')

        self.queue = Queue()

        self.server, self.port = server.split(':')

        log.debug('using a threadpool of size: %d' % threadpool_size)

        # build threadpool
        self.threadpool = [
            threading.Thread(target=self.worker) for i in range(threadpool_size)
        ]

    def start(self):

        log.info('downloading Alexas sites from %s' % self.ALEXA_URL)
        path = os.path.join(tempfile.gettempdir(), 'alexas-cache')

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

        with open(path, 'r') as fd:
            print(fd)
            zfd = zipfile.ZipFile(fd)
            data = StringIO.StringIO(zfd.read(self.FILENAME))
            reader = csv.reader(data)

            for row in reader:
                log.debug(row[1])
                self.queue.put(row[1])


        log.info('starting processing...')

        for thread in self.threadpool:
            thread.setDaemon(True)
            thread.start()

        log.info('%d domain names loaded'  % self.queue.qsize())
        self.queue.join()

    def worker(self):
        log.debug('thread starting....')
        while True:
            try:
                item = self.queue.get()
                log.debug('processing %s' % item )
                message = dns.message.make_query(item, 'A')
                response = dns.query.udp(message, self.server, port=int(self.port))
                log.debug('processing %s completed' % item )
                self.queue.task_done()
            except Exception as e:
                log.exception(e)
                return