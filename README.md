Note : The current server handle requests for all the product types listed on GDAX
       We have even checked for reverse request i.e for example for ETH-BTC order book we have checked with base_currency BTC and quote currency ETH for a given amount

1) Dependencies 
	a) Framework used : 	Flask 
	 			Use the below command to install flask
	  			==> pip install flask


2) To run the server , run the below command
==> python Server.py

This command will start the server to handle POST requests and serve them


3) Once our server is up and running, we can test it using different methods. 

==> You can use the below curl commands to test it.
Sample tests :  curl -i -X POST -H 'Content-Type: application/json' -d '{"action" : "sell", "base_currency" : "BTC", "quote_currency" : "USD", "amount":"5.0"}' http://127.0.0.1:5000/quote
         	curl -i -X POST -H 'Content-Type: application/json' -d '{"action" : "buy", "base_currency" : "LTC", "quote_currency" : "USD", "amount":"1.0"}' http://127.0.0.1:5000/quote
