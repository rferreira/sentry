import sys, logging, re, random
import dns
import dns.message
import dns.query

import sentry.parser
from sentry.errors import Error
from sentry.net import Server
from sentry import rules

log = logging.getLogger(__name__)

def _pprint_message(message):
    return 'M{ id: %s, flags: %s question: %s }' % (message.id, message.flags, message.question)

class Sentry(object):
    """
    sentry is dns for fun and profit
    """ 
    REQUIRED_CONFIG_ENTRIES = ['port', 'rules', 'host', 'catchall_address']

    def __init__(self, settings):
        log.debug('settings:')
        log.debug(settings)  
        self.settings = settings  

        self.ruleset = sentry.parser.parse(settings)

    def process(self, packet):        
        message = dns.message.from_wire(packet)   
        message.__class__.__str__ = _pprint_message

        log.debug(message)
       
        for rule in self.ruleset:
            m = rule.RE.search(str(message.question[0].name))
            if m is not None:
                log.debug('resolving query: %s using : %s ' % (message,rule) )
                response = rule.dispatch(message)
                
                if response is None:
                    break

                # sending rule response back to client
                return response

        raise Exception('No matching rule for %s found' % message)

    def start(self):
        log.info('starting, %d known rules' % (len(self.ruleset)))
        server = Server(self.settings['host'], self.settings['port'], self.process)
        server.start()

