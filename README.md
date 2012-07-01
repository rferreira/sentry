# sentry - dns for fun and profit!

Sentry is a DNS proxy that allows you to inspect, block, rewrite and resolve queries. 


## Installing

1. Download sentry 
2. pip install . (in the directory containing sentry)


## Configuring

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

## Rules and doing things you never thought possible with DNS

