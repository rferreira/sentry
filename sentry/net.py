import asyncore
import logging, sys, os, socket, time, threading
from collections import deque
from multiprocessing import Queue

from sentry import errors
from sentry import stats

log = logging.getLogger(__name__)


class Server(asyncore.dispatcher):
    """
    Handles all network io
    """
    def __init__(self, host, port, onreceive, threadpool_size):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.host = host
        self.port = port

        # io buffers
        self.buffer_in = deque()
        self.buffer_out = deque()

        self.onreceive = onreceive

        self.request_queue = Queue()

        log.debug('using a threadpool of size: %d' % threadpool_size)

        # build threadpool
        self.threadpool = [
            threading.Thread(target=self.worker) for i in range(threadpool_size)
        ]

        for thread in self.threadpool:
            thread.setDaemon(True)
            thread.start()

        self.active_threads = 0

        self.bind((host, port))
        log.info("Server started on %s:%s" %  (self.addr) )

    def handle_read(self):
        data, addr = self.recvfrom(1024)
        if not data:
            self.close()
            return
        stats.add('net.packets_received', 1)
        stats.add('net.bytes_received', len(data))
        self.request_queue.put( (data, addr ))

    def handle_close(self):
        pass

    def handle_connect(self):
        pass

    def handle_accept(self):
        pass

    def handle_write(self):
        while len(self.buffer_out) > 0:
            addr, packet = self.buffer_out.popleft()
            s = self.socket.sendto(packet, addr)
            stats.add('net.packets_sent', 1)
            stats.add('net.bytes_sent', s)

    def writable(self):
        if len(self.buffer_out) > 0:
            return True

    def handle_error(self):
        log.exception(sys.exc_value)

    def start(self):
        self.running = True
        while self.running:
            try:
                asyncore.loop(timeout=0.5, use_poll=False, count=1)
            except KeyboardInterrupt as k:
                self.stop()

    def stop(self):
        self.running = False
        log.debug('network node stopped.')
        return

    def worker(self):
        log.debug('threading starting...')
        while True:
            data, addr = self.request_queue.get()
            self.active_threads += 1
            stats.add_avg('net.active_threads', self.active_threads)
            try:
                response = self.onreceive(data, {
                    'client' : '%s:%s' % (addr),
                    'server' : '%s:%s' % (self.host, self.port)
                    })

                self.buffer_out.append( (addr, response))
            except Exception as e:
                log.exception(e)

            self.active_threads -= 1
            stats.add_avg('net.active_threads', self.active_threads)



