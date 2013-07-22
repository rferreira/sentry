import sys, logging, re, time, signal, os

import dns
import dns.message
import dns.query

import prettytable

import sentry.parser
from sentry.network import Server
from sentry import rules, errors, stats, domain_stats
from sentry.counter import count_calls

log = logging.getLogger(__name__)

def _pprint_message(message):
    return 'M{ id: %s, flags: %s question: %s }' % (message.id, message.flags, message.question)

class Sentry(object):
    """
    sentry is dns for fun and profit
    """
    REQUIRED_CONFIG_ENTRIES = ['port', 'rules', 'host', 'catchall_address']

    def __init__(self, settings):
        self.settings = settings
        signal.signal(30, self.usr1_signal_handler)

        self.ruleset = sentry.parser.parse(settings)

        stats.set_type('response_time', 'int')

    def process(self, packet, context):
        stats.inc_ops('requests')
        start_time = time.time()

        message = dns.message.from_wire(packet)
        message.__class__.__str__ = _pprint_message

        log.debug(message)
        log.debug(context)

        for rule in self.ruleset:
            m = rule.RE.search(str(message.question[0].name))
            if m is not None:
                log.debug('resolving query: %s using : %s ' % (message,rule) )
                response = rule.dispatch(message, context=context)

                # updating stats for this rule being called
                stats.add(rule.__class__,1)

                # rules that return none ignored
                if response is None:
                    continue

                # updating stats
                stats.dec_ops('requests')
                stats.add_avg('response_time_msec', (time.time() - start_time)*1000 )
                domain_stats.add( str(message.question[0].name).strip(), 1)

                # sending rule response back to client
                return response

        stats.add('requests_failed',1)
        raise errors.Error('No matching rule for %s found' % message)

    def start(self):
        log.info('starting, %d known rules' % (len(self.ruleset)))
        server = Server(self.settings['host'], self.settings['port'], self.process, self.settings.get('threadpool_size',1) )
        server.start()

        log.info('shutting down, dumping stats:')

        self.usr1_signal_handler(None, None)

    def usr1_signal_handler(self,num, frame):
        log.debug('dumping stats:')
        x = prettytable.PrettyTable(['metric', 'value'])
        x.align = 'l'

        for r in stats.get_metrics():
            x.add_row([r['name'], r['value']])


        y = prettytable.PrettyTable(['domain', 'queries'])
        y.align = 'l'

        for r in domain_stats.get_metrics(include_uptime=False):
            y.add_row([r['name'], r['value']])

        log.info('system stats: \n' + str(x) )
        log.info('domain stats: \n ' + y.get_string(sortby='queries', reversesort=True) )








