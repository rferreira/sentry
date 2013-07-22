
import logging, sys, os, socket, time, threading, futures

from sentry import errors, stats, profile


log = logging.getLogger(__name__)


class Server(object):
    """
    Handles all network io
    """
    def __init__(self, host, port, onreceive, threadpool_size):

        # udp socket binding
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # tcp socket binding
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.host = host
        self.port = port

        self.onreceive = onreceive

        log.debug('using a threadpool of size: %d' % threadpool_size)

        self.threadpool = futures.ThreadPoolExecutor(max_workers=threadpool_size)
        self.pollers = futures.ThreadPoolExecutor(max_workers=1)

        self.active_threads = 0

        self.udp_socket.bind((host, port))
        self.tcp_socket.bind((host, port))

        log.info("Server started on %s:%s" %  (self.host, self.port) )


    def udp_poller(self):
        while not self.stopping:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if not data:
                    self.close()
                    return
                stats.add('net.packets_received', 1)
                stats.add('net.bytes_received', len(data))
                self.threadpool.submit(self.worker, (data, addr))

            except Exception as ex:
                log.exception(ex)


    def start(self):
        self.stopping = False
        self.udp_poller_thread = threading.Thread(None, self.udp_poller, name='udp-poller')
        self.udp_poller_thread.setDaemon(True)
        self.udp_poller_thread.start()

        while not self.stopping:
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                log.info('stopping')
                self.stop()


    def stop(self):
        self.stopping = True
        log.debug('network node stopped.')
        return

    @profile.howfast
    def worker(self, info):
        log.debug('starting to process request...')
        data, addr = info
        self.active_threads += 1
        stats.add_avg('net.active_threads', self.active_threads)
        try:
            response = self.onreceive(data, {
                'client' : '%s:%s' % (addr),
                'server' : '%s:%s' % (self.host, self.port)
                })

            s = self.udp_socket.sendto(response, addr)
            stats.add('net.packets_sent', 1)
            stats.add('net.bytes_sent', s)
            log.debug('finished to process request...')

        except Exception as e:
            log.exception(e)

        self.active_threads -= 1
        stats.add_avg('net.active_threads', self.active_threads)



