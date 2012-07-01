### Sentry - dns for fun and profit!

Sentry is a DNS proxy that allows you to inspect, block, rewrite, redirect and resolve queries in-flight. 

### Installing

1. Download sentry 
2. pip install . (in the directory containing sentry)

### Configuring

You should start up with a basic json config file like this: 

    {
        "port" : 5300,
    	"host" : "0.0.0.0",
    	"rules" : [
    		"resolve ^(.*) using 8.8.4.4, 8.8.8.8"
    	]	
    }
    
The example above tells sentry to: 

* listen on port 5300 (udp)
* resolve all inbound queries using DNS servers 8.8.4.4 and 8.8.8.8 (google's public DNS servers)

### Running it

To run sentry you just need to pass it the config file you created: 

    $ sentry -c CONFIG 
    [07/01/2012 06:38:28] [sentry] INFO: using config: sentry.config
    [07/01/2012 06:38:28] [sentry.core] INFO: starting, 1 known rules
    [07/01/2012 06:38:28] [sentry.net] INFO: Server started on 0.0.0.0:5300

For the prestige, you can use dig to verify sentry is responding to requests:

    dig @localhost -p 5300 nytimes.com

### Rules - doing things you never thought possible with DNS

Sentry allows you to log, block, rewrite, redirect and resolve queries based upon simple rules that are matched, in order, against the inbound DNS query. 

**Redirecting a query:**

A redirect rule can redirect an inbound requests to nytimes.com to google.com with a CNAME response. 

    "redirect ^(.*)nytimes.com to google.com"
    		
Now, for the prestige: 

    $ dig @localhost -p 5300 nytimes.com

    ; <<>> DiG 9.7.3-P3 <<>> @localhost -p 5300 nytimes.com
    ; (3 servers found)
    ;; global options: +cmd
    ;; Got answer:
    ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 56474
    ;; flags: qr rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
    ;; WARNING: recursion requested but not available

    ;; QUESTION SECTION:
    ;nytimes.com.			IN	A

    ;; ANSWER SECTION:
    nytimes.com.		300	IN	CNAME	google.com.

    ;; Query time: 502 msec
    ;; SERVER: 127.0.0.1#5300(127.0.0.1)
    ;; WHEN: Sun Jul  1 00:37:17 2012
    ;; MSG SIZE  rcvd: 50

**Logging a query:**

A log rule tells sentry to log an inbound queries matching a certain regular expression

    "log ^(.*)google.com"
    
    
**Blocking a query:**

A block rule tells sentry to return an empty response to all queries matching a certain regular expression 

    "block ^(.*).xxx"
    
**Resolving a query:**

A resolve rule tells sentry to return to resolve all queries matching a certain regular expression using one, or more, upstream DNS servers

    ""resolve ^(.*)facebook.com using 10.10.1.2 ","
    		
\* If you would like your sentry server to resolve all inbound requests you must include at the bottom of your rules list a catch all entry like below: 

    "resolve ^(.*) using 8.8.4.4, 8.8.8.8"
    
**Here's an example of a configuration file including multiple rules:**

    {
    	"port" : 5300,
    	"host" : "0.0.0.0",
    	"rules" : [
    		"block ^(.*)youtube.com",		
    		"block ^(.*).xxx",
    		"log ^(.*)google.com",

    		"rewrite ^www.google.com to google.com",		

    		"redirect ^(.*)nytimes.com to google.com",					
    		"redirect ^(.*)reddit.com to google.com",

    		"resolve ^(.*)facebook.com using 10.10.1.2 ",
    		"resolve ^(.*) using 8.8.4.4, 8.8.8.8"
		

    	]	
    }

### Sentry Metrics

Like metrics? Just send sentry a SIGUSR1 posix signal and bam! 

sending the signal (replace $PID with sentry's process id):

    $ kill -30 $PID

output in the sentry log: 

    [07/01/2012 00:57:12] [sentry.core] INFO: system stats: 
    +-------------------------------------+---------------+
    | metric                              | value         |
    +-------------------------------------+---------------+
    | net.bytes_received                  | 85            |
    | net.bytes_sent                      | 458           |
    | net.packets_received                | 3             |
    | net.packets_sent                    | 3             |
    | requests_pending                    | 0             |
    | requests_total                      | 3             |
    | response_time_msec_avg              | 3.07466666667 |
    | response_time_msec_max              | 4.138         |
    | response_time_msec_min              | 1.435         |
    | uptime                              | 23.628207922  |
    | <class 'sentry.rules.RedirectRule'> | 1             |
    | <class 'sentry.rules.LoggingRule'>  | 2             |
    | <class 'sentry.rules.ResolveRule'>  | 2             |
    +-------------------------------------+---------------+
    [07/01/2012 00:57:12] [sentry.core] INFO: domain stats: 
     +--------------+---------+
    | domain       | queries |
    +--------------+---------+
    | google.com.  | 2       |
    | nytimes.com. | 1       |
    +--------------+---------+

