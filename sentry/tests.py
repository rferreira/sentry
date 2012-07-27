import unittest, logging, sys

import dns
import dns.rrset
import dns.query
import dns.name

from sentry.core import Sentry
from sentry import LOG_FORMAT

log = logging.getLogger('sentry')
logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)

class SentryTests(unittest.TestCase):

	context = {
	    'client' : '%s:%s' % ('1.1.1.1',5300),
	    'server' : '%s:%s' % ('2.2.2.2', 1000)
     }
	
	def test_block_rule(self):
		sentry = Sentry({
			'rules' : [ 
				'block ^(.*).xxx'
			 ]
		})
		message = dns.message.make_query('foo.xxx', 'A')
		r = sentry.process(message.to_wire(), self.context)
		response = dns.message.from_wire(r)
		assert len(response.answer) is 0

	def test_do_not_block_rule(self):
		sentry = Sentry({
			'rules' : [ 
				'block ^(.*).xxx',
				'resolve ^(.*) using 8.8.4.4, 8.8.8.8'
			 ]
		})
		message = dns.message.make_query('foo.com', 'A')
		r = sentry.process(message.to_wire(), self.context)
		response = dns.message.from_wire(r)
		assert len(response.answer) is not 0

	def test_conditional_blocks(self):
		sentry = Sentry({
			'rules' : [ 
				'block ^(.*).xxx if type is TXT',
				'block ^(.*).xxx if type is MX and class is ANY',				
				'block ^(.*).xxx if class is ANY'
			 ]
			})

		message = dns.message.make_query('foo.xxx', 'TXT')

		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0

		message = dns.message.make_query('foo.xxx', 'MX', rdclass=dns.rdataclass.ANY)

		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0


		message = dns.message.make_query('foo.xxx', 'A', rdclass=dns.rdataclass.ANY)

		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0

	def test_resolve(self):
		sentry = Sentry({
			'rules' : [ 
				'resolve ^(.*) using 8.8.4.4, 8.8.8.8'
			 ]
			})

		message = dns.message.make_query('google.com', 'MX')

		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is not 0

	def test_mix_blocks(self):
		sentry = Sentry({
			'rules' : [ 
				'block ^(.*).xxx',
				'block ^(.*).edu if type is MX and class is ANY',	
				'block ^(.*).biz if class is ANY',	
				'resolve ^(.*) using 8.8.4.4, 8.8.8.8'			
			 ]
			})

		# should get blocked
		message = dns.message.make_query('foo.xxx', 'A')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0

		# should get blocked
		message = dns.message.make_query('foo.xxx', 'MX')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0

		# should not get blocked
		message = dns.message.make_query('asu.edu', 'TXT')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is not 0

		# should not get blocked
		message = dns.message.make_query('google.biz', 'TXT')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is not 0

		# should not get blocked
		message = dns.message.make_query('asu.edu', 'A')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is not 0

		# should get blocked
		message = dns.message.make_query('asu.edu', 'MX', rdclass=dns.rdataclass.ANY )
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		assert len(response.answer) is 0


	def test_redirect(self):
		sentry = Sentry({
			'rules' : [ 
				'redirect ^(.*)nytimes.com to google.com',		
			 ]
			})

		
		message = dns.message.make_query('nytimes.com', 'A')
		r = sentry.process(message.to_wire(), self.context)

		response = dns.message.from_wire(r)
		
		assert response.answer[0].rdtype is dns.rdatatype.CNAME
		assert response.answer[0].rdclass is dns.rdataclass.IN

		self.assertEqual(response.answer[0].to_text(),'nytimes.com. 300 IN CNAME google.com.')


if __name__ == '__main__':
	unittest.main()


