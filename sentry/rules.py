import sys, logging, re, random

import dns
import dns.rrset
import dns.query
import dns.name

from sentry import stats, errors

log = logging.getLogger(__name__)
RETRIES = 3
DEFAULT_TTL = 300
DEFAULT_TIMEOUT = 1.0

class Rule(object):
    """
    Parent class for all rules.

    - rules can return either None or a valid response. None responses are ignored.

    """

    def __init__(self, settings, domain, args):
        self.domain = domain
        self.RE = re.compile(domain)
        self.settings = settings

    def dispatch(self, message, *args, **extras):
        log.info('dummy act being called, nothing will happen')
        pass

    def __str__(self):
        return 'rule [%s] domain [%s]' % (self.__class__, self.domain)

class RedirectRule(Rule):
    """
    redirects a query using a CNAME
    """
    SYNTAX = [
        # redirect ^(.*)google.com to nytimes.com
        re.compile(r'^redirect (?P<domain>.*) to (?P<destination>.*)$',flags=re.MULTILINE)
    ]

    def __init__(self, settings, domain, args):
        self.dst = str(args['destination'])
        if not self.dst.endswith('.'):
            self.dst += '.'

        super(RedirectRule,self).__init__(settings, domain, args)

    def dispatch(self, message, *args, **extras):
        response = dns.message.make_response(message)
        response.answer.append(
            dns.rrset.from_text(message.question[0].name, DEFAULT_TTL, dns.rdataclass.IN, dns.rdatatype.CNAME, self.dst)
        )

        return response.to_wire()

class BlockRule(Rule):
    """
    blocks the request by simply returning an empty response
    """
    SYNTAX = [
        # block ^(.*)exmaple.xxx
        re.compile(r'^block (?P<domain>.*)$',flags=re.MULTILINE)
    ]

    def dispatch(self, message, *args, **extras):
        context = extras.pop('context', {})
        log.warn('blocking query: %s matched by rule: %s with context: %s' % (message.question[0].name, self.domain, context) )
        response = dns.message.make_response(message)
        return response.to_wire()

class ConditionalBlockRule(Rule):
    """
    blocks the request based upon some simple if logic
    """

    SYNTAX = [
        #block ^(.*).xxx if type is MX and class is ANY
        re.compile(r'^block (?P<domain>.*) if type is (?P<type>.*) and class is (?P<class>.*)$',flags=re.MULTILINE),
        # block ^(.*).xxx if type is TXT
        re.compile(r'^block (?P<domain>.*) if type is (?P<type>.*)$',flags=re.MULTILINE),
        # block ^(.*).xxx if class is ANY
        re.compile(r'^block (?P<domain>.*) if class is (?P<class>.*)$',flags=re.MULTILINE),
    ]

    def __init__(self, settings, domain, args):

        self.rdtype  = args.get('type', None)

        if self.rdtype is not None:
            self.rdtype  = dns.rdatatype.from_text( args.get('type', 'A' ))

        self.rdclass = args.get('class', None)

        if self.rdclass is not None:
            self.rdclass = dns.rdataclass.from_text(args.get('class', 'IN' ))

        super(ConditionalBlockRule,self).__init__(settings, domain, args)

    def dispatch(self, message, *args, **extras):
        context = extras.pop('context', {})

        q = message.question[0]


        if self.rdtype is not None and q.rdtype != self.rdtype:
            return None

        if self.rdclass is not None and q.rdclass != self.rdclass:
            return None

        log.warn('conditionally blocking query: %s matched by rule: %s with context: %s' % (message.question[0].name, self.domain, context) )

        response = dns.message.make_response(message)

        return response.to_wire()


class LoggingRule(Rule):
    """
    logs the query and nothing else
    """
    SYNTAX = [
        # log ^(.*)example.com
        re.compile(r'^log (?P<domain>.*)$',flags=re.MULTILINE)
    ]

    def dispatch(self,message, *args, **extras):
        context = extras.pop('context', {})
        log.info('logging query: %s matched by rule: %s with context: %s' % (message.question[0].name, self.domain, context) )
        return None


class ResolveRule(Rule):
    """
    resolves a query using a specific DNS Server
    """

    SYNTAX = [
        # resolve ^(.*)example using 8.8.4.4, 8.8.8.8
        re.compile(r'^resolve (?P<domain>.*) using (?P<resolvers>.*)$',flags=re.MULTILINE)
    ]

    def __init__(self, settings, domain, args):
        resolvers = args.get('resolvers', None)

        self.resolvers =  map(lambda x: x.strip(), resolvers.split(','))
        log.debug('resolvers: %s' % self.resolvers)

        # how long we wait on upstream dns servers before puking
        self.timeout = settings.get('resolution_timeout', DEFAULT_TIMEOUT)
        log.debug('timeout: %d' % self.timeout)

        super(ResolveRule,self).__init__(settings, domain, args)

    def dispatch(self, message, *args, **extras):
        for x in xrange(RETRIES):
            try:
                response = dns.query.udp(message, random.choice(self.resolvers), timeout=self.timeout)
                return response.to_wire()
            except Exception as e:
                log.exception(e)

            raise errors.NetworkError('could not resolve query %s using %s' % (message, self.resolvers))

class RewriteRule(Rule):
    """
    applies a regex to a inbound request

    # note: rewrite rules are experimental and might not work with all DNS clients
    """

    SYNTAX = [
        # rewrite ^www.google.com to google.com
        re.compile(r'^rewrite (?P<domain>.*) to (?P<pattern>.*)$',flags=re.MULTILINE)
    ]

    def __init__(self, settings, domain, args):
        self.pattern = args['pattern']
        super(RewriteRule,self).__init__(settings, domain, args)

    def dispatch(self, message, *args, **extras):
        log.debug('domain: %s pattern: %s message: %s' % (self.domain, self.pattern, message))
        message.question[0].name = dns.name.from_text(self.pattern)

        return None
