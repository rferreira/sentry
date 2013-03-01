{
	"port" : 5300,
	"host" : "0.0.0.0",
	"threadpool_size" : 1,
	"rules" : [
		"block ^(.*)porn|penis|bang|anal|sex|cunt|fuck|sex|cock|pussy(.*).(.*)",
		"block ^(.*).xxx",
		"block ^(.*)whitehouse.com",

		"log ^(.*)youtube.com",
		"log ^(.*)disney(.*).com",
		"log ^(.*)amazon(.*).com",

		"resolve ^(.*) using 8.8.4.4, 8.8.8.8"

	]
}