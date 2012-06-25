import sys, logging, re, random
import dns
import dns.message
import dns.query

import sentry.parser
from sentry.errors import Error
from sentry.net import Server

log = logging.getLogger(__name__)

class Sentry(object):
    """
    sentry is dns for fun and profit
    """ 
    REQUIRED_CONFIG_ENTRIES = ['port', 'rules', 'upstream', 'host', 'catchall_address']

    def __init__(self, settings):
        log.debug('settings:')
        log.debug(settings)  
        self.settings = settings  

        log.debug(settings.keys())

        self.ruleset = sentry.parser.parse(settings)

    def process(self, packet):        
        message = dns.message.from_wire(packet)            
        log.debug(message)
       
        for rule in self.ruleset:
            m = rule.RE.search(str(message.question[0].name))
            if m is not None:
                log.debug('wow found a rule that matches (%s) - dispatching' % rule)
                response = rule.dispatch(message)
                if response is None:
                    break

                return response

            
        # catchall - simple upstream resolve
        log.debug('no rules match query, sending upstream...')        
            
        response = dns.query.udp(message, random.choice(self.settings['upstream']))  
        return response.to_wire()



    def start(self):
        log.info('starting, %d known rules' % (len(self.ruleset)))

        server = Server(self.settings['host'], self.settings['port'], self.process)
        server.start()
