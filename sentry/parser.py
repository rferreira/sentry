
import re, sys, logging
from sentry import rules

log = logging.getLogger(__name__)

RULES = [
	rules.RedirectRule,
	rules.BlockRule, 	
	rules.ConditionalBlockRule,
	rules.LoggingRule,
	rules.ResolveRule,
	rules.RewriteRule,

]

def parse(settings):
	"""
	matches the syntax rules for every known rule against lines in the config 
	"""
	
	ruleset = []
	matched = False	
	
	# breaking up ruleset
	for line in settings['rules']:
		log.debug('parsing: %s' % line)		

		# for every rule we known of:
		for rule in RULES:

			# for every syntax of that rule
			for re in rule.SYNTAX:
				match = re.search(line)		

				if match is not None:
					try:
						log.debug('line %s matched by %s' % (line, re) )
						domain = match.group('domain').strip()
						ruleset.append(rule(settings, domain, match.groupdict() ))	

						matched = True	
						# if we found a match, we don't keep looking
						break

					except Exception as e:
						log.error('syntax error in line: %s - skipping' % line)	
						log.exception(e)

		if not matched:
			log.info('no rules match line [%s] ignoring it' % line)
			
		matched = False

	log.debug(ruleset)
	return ruleset


