import sys, logging, re
import dns

log = logging.getLogger(__name__)

class Rule(object):
	def __init__(self, domain):
		self.domain = domain
		self.RE = re.compile(domain)

	def dispatch(self,request):
		log.info('dummy act being called, nothing will happen')
		pass

	def __str__(self):
		return 'rule: %s domain: %s' % (self.__class__, self.domain)

class RedirectRule(Rule):	
	"""
	redirects a query using a CNAME
	"""

	def __init__(self, domain, dst):
		self.dst = str(dst)
		if not self.dst.endswith('.'):
			self.dst += '.'
			
		super(RedirectRule,self).__init__(domain)

	def dispatch(self,request):
		response = dns.message.make_response(request)
		response.answer.append(
			dns.rrset.from_text(request.question[0].name, 1000, dns.rdataclass.IN, dns.rdatatype.CNAME, self.dst)
		)

		return response.to_wire()

class BlockRule(Rule):		
	def dispatch(self,request):
		response = dns.message.make_response(request)
		response.answer.append(
			dns.rrset.from_text(request.question[0].name, 1000, dns.rdataclass.IN, request.question[0].rdclass, '74.125.224.64')
		)

		return response.to_wire()

class LoggingRule(Rule):
	"""
	logs the query and nothing else	
	"""	
	def dispatch(self,request):
		log.info('logging query: %s matched by rule: %s' % (request.question[0].name, self.domain) )
		return None

