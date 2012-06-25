
import re, sys, logging
from sentry import rules

log = logging.getLogger(__name__)

RE_BLOCK = re.compile(r'^block (?P<domain>.*)$',flags=re.MULTILINE)
RE_LOG = re.compile(r'^log (?P<domain>.*)$',flags=re.MULTILINE)
RE_REDIRECT = re.compile(r'^redirect (?P<domain>.*) to (?P<destination>.*)$',flags=re.MULTILINE)

def parse(entries):

	ruleset = []

	for line in entries:
		log.debug('parsing: %s' % line)
		
		# block
		match = RE_BLOCK.search(line)		
		if match is not None:
			try:
				log.debug('found block rule, processing it')
				domain = match.group('domain').strip()
				ruleset.append(rules.BlockRule(domain))
			except Exception as e:
				log.error('syntax error in line: %s - skipping' % line)	
				log.exception(e)
		# log
		match = RE_LOG.search(line)		
		if match is not None:
			try:
				log.debug('found logging rule, processing it')
				domain = match.group('domain').strip()
				ruleset.append(rules.LoggingRule(domain))
			except Exception as e:
				log.error('syntax error in line: %s - skipping' % line)	
				log.exception(e)

		# redirect
		match = RE_REDIRECT.search(line)		
		if match is not None:
			try:
				log.debug('found redirect rule, processing it')
				domain = match.group('domain').strip()
				destination = match.group('destination').strip()
				ruleset.append(rules.RedirectRule(domain,destination))
			except Exception as e:
				log.error('syntax error in line: %s - skipping' % line)	
				log.exception(e)

	return ruleset

