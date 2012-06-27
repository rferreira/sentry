import asyncore
import logging, sys, os, socket, time, threading
from collections import deque

from sentry import errors

log = logging.getLogger(__name__)

class TBucket(object):
    """ Simple wrapper objects for storing test run telemetry"""
    
    BYTES_IN = 0
    BYTES_OUT = 1
    PACKETS_OUT = 2
    START_TIME = 3
    END_TIME = 4
    PACKETS_IN = 5
    
    def __init__(self):     
        self.store = [0.0] * 10
        
    def add(self, s):
        log.info('source:')
        log.info(s)
        log.info('self:')
        log.info(self)
            

    def time_elapsed(self):
        return round(self.store[TBucket.END_TIME] - self.store[TBucket.START_TIME],4)
        
    def transfer_rate(self, in_mega_bytes=True):
        tr = (self.store[TBucket.BYTES_OUT] + self.store[TBucket.BYTES_IN])/self.time_elapsed()
        
        if in_mega_bytes:
            return round(tr/1024.0/1024.0,2)
        
        return round(tr,2)
    
    def packets_out(self):
        return round(self.store[TBucket.PACKETS_OUT],2)

    def packets_in(self):
        return round(self.store[TBucket.PACKETS_IN],2)
        
    
    def mbytes_in(self):
        return round(self.store[TBucket.BYTES_IN]/1024/1024,2)
        
    def mbytes_out(self):
        return round(self.store[TBucket.BYTES_OUT]/1024/1024,2)
    
    def start(self):
            self.store[TBucket.START_TIME] = time.time()

    def get_start(self):
        return self.store[TBucket.START_TIME]

    def get_end(self):
        return self.store[TBucket.END_TIME]

    def end(self):
        self.store[TBucket.END_TIME] = time.time()
        
    def packet_transfer_rate(self):
        return round((self.store[TBucket.PACKETS_OUT] + self.store[TBucket.PACKETS_IN])/self.time_elapsed(),2)
    
    def add(self, tb):
        
        # list comprehension magic  
        tmp = [ sum(p) for p in zip(self.store,tb.store) ]

        # dealing intelligently with time       
        tmp[TBucket.START_TIME] = tb.get_start() if tb.get_start() < self.get_start() or self.get_start() == 0.0 else self.get_start()
        tmp[TBucket.END_TIME] = tb.get_end() if tb.get_end() > self.get_end() or self.get_end() == 0.0 else self.get_end()

        self.store = tmp

class Server(asyncore.dispatcher):
    """
    Handles all network io
    """
    def __init__(self, host, port, onreceive):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
                
        self.packets_sent = 0
        self.packets_rcv = 0
        self.bytes_sent = 0
        self.bytes_rcv = 0

        self.stats = TBucket()
        self.stats.start()

        # io buffers
        self.buffer_in = deque()
        self.buffer_out = deque()

        self.onreceive = onreceive

        self.bind((host, port))
        log.info("Server started on %s:%s" %  (self.addr) )
        # server monitoring thread:
        t = threading.Thread(target=self.status_thread)
        t.setDaemon(True)
        t.start()            
                
    def handle_read(self):
        data, addr = self.recvfrom(1024)
        if not data:
            self.close()
            return
        self.packets_rcv += 1
        self.bytes_rcv += len(data)
        try:
            response = self.onreceive(data)
            self.buffer_out.append( (addr, response))
        except Exception as e:
            log.exception(e)


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
            self.packets_sent += 1
            self.bytes_sent += s            
                  
    def writable(self):
        if len(self.buffer_out) > 0:
            return 1
            
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
        self.stats.end()        
        log.info('network node stopped.')        
            
    def status_thread(self):
        time.sleep(60)
        while True:            
            log.info('packets in: %d packets out: %d buffer_in: %d buffer_out: %d uptime: %d sec' % (self.packets_rcv, self.packets_sent,  len(self.buffer_in), len(self.buffer_out), time.time() - self.stats.get_start() ))
            time.sleep(60*60*1)

        
