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