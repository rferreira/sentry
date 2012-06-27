import sys, logging, re, random
import dns, dns.query

log = logging.getLogger(__name__)
RETRIES = 3

class Rule(object):
    """ Parent class for all rules """

    def __init__(self, settings, domain):
        self.domain = domain
        self.RE = re.compile(domain)
        self.settings = settings

    def dispatch(self,message):
        log.info('dummy act being called, nothing will happen')
        pass

    def __str__(self):
        return 'rule [%s] domain [%s]' % (self.__class__, self.domain)

class RedirectRule(Rule):   
    """
    redirects a query using a CNAME
    """
    def __init__(self, settings, domain, dst):
        self.dst = str(dst)
        if not self.dst.endswith('.'):
            self.dst += '.'
            
        super(RedirectRule,self).__init__(settings, domain)

    def dispatch(self,message):
        response = dns.message.make_response(message)
        response.answer.append(
            dns.rrset.from_text(message.question[0].name, 1000, dns.rdataclass.IN, dns.rdatatype.CNAME, self.dst)
        )

        return response.to_wire()

class BlockRule(Rule):      
    def dispatch(self,message):
        to = str(self.settings['catchall_address'])     
        response = dns.message.make_response(message)
        response.answer.append(
            dns.rrset.from_text(message.question[0].name, 1000, dns.rdataclass.IN, message.question[0].rdclass, to )
            )
        return response.to_wire()

class LoggingRule(Rule):
    """
    logs the query and nothing else 
    """ 
    def dispatch(self,message):
        log.info('logging query: %s matched by rule: %s' % (message.question[0].name, self.domain) )
                

class ResolveRule(Rule):    
    """
    resolves a query using a diff  a specific DNS Server 
    """    

    def __init__(self, settings, domain, resolvers):
        self.resolvers =  map(lambda x: x.strip(), resolvers.split(','))
        log.debug('resolvers: %s' % self.resolvers)
    
        super(ResolveRule,self).__init__(settings, domain)

    def dispatch(self,message):        
        for x in xrange(RETRIES):                  
            try:
                response = dns.query.udp(message, random.choice(self.resolvers))   
                return response.to_wire()
                    
            except Exception as e:
                log.exception(e)

            log.error('could not resolve query %s using %s' % (message, self.resolvers))
            return None

        