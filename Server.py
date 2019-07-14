'''
File : Server.py

Purpose : To handle API requests to serve and return Quote for a given base and quote currency pair based on required amount
	 ** WE handle requests for all the listed product types on GDAX**

Phase 2 : **Future changes***(for Real-life low-latency throughput, debug level processing  and more validation)
==> 1) We need to use the websocket feed available to retrieve real time data and update it.
    2) We need to use a Balanced binary tree to store all the entries from the order book 
    3) We need to keep a track of all Match messages as well for processing entries
    4) Doing this we can work and real-time data on the same websocket connection, instead of making a get request for the orderbook for a given product_type, which we are currently doing.
       Becuase, using the websocket connection can allow us to access data on the same connection, where every getrequest in this case will open a new connection("Until Kepp-alive is set")
	which will act as an extra over-head
    5) All this data is available on GDAX website , which can be viewed along with the currently used technique

	
    6) Introduce logging to log all the requests  and keep log_level so we can introduce it and check in case of any error

    7) ** we need to put a validation on the minimum and maximum size before sending quote and making transcation using the base_min_size and base_max_size
'''

from flask import Flask, request, jsonify,abort, make_response
import sys
import requests
import json

baseUrl  = "http://api.gdax.com"

#Maintain a virtual list of all the product pairs to make sure that we can check what is the correct combo to go for in that case, before requesting the order book
prodListDict = {}

app = Flask(__name__)

'''
Function : 	getRequest()

Parameters : 	Uri -> Uri to access at the base URl
		Param -> Additional parameters to be added while making the request

Purpose :	To perform a get request for the given URI at the given base URL

Return : "error" -> in case of error
	 result -> if the status code recieved is 200 for request
'''
def getRequest(Uri, param):
	try:

		finalUrl = baseUrl + Uri		
		result = requests.get(url = finalUrl, params = param)
		
		if result.status_code == 200:
			return result
		else:
			return "error"		
	
	except requests.exceptions.RequestException as e:
		print "Exception in GET Request"
		return "error"

'''
Functon : InitListofProducts()

Parameters : None

Purpose  : To obtain a list of all the valid products from GDAX

Return : True -> if the list is initialized successfully
	 False -> in case of any error
'''
def InitListofProducts():
	result = getRequest("/products", {})
	
	if result != "error":
		#print result.content
		prodList = json.loads(result.content)
		
		#Store a list of all the products in a dict
		for obj in prodList:
			prodListDict[obj["id"]] = obj

		return True
	else:
		return False



'''
Function : getOrderBook()

Parameters : product_type

Purpose : To retrieve order book of a given product type and return it.

Return : True, OrderBook -> if order book for the given product type was retrieved successfully.
	 False, ErrorMsg -> in case of any error.
'''
def getOrderBook(product_type):
	PARAM = {"level" : 2}

	result = getRequest("/products/"+product_type+"/book", PARAM)

	if result != "error":
		return True, result.content
	else:
		return False, "Failed to retrieve Order Book"

'''
Function : processRequest()

Parameters : action, base_currency, quote_currency, amount

Purpose : To process request to return a quote to the given user

Return : True, Quote -> if the quote was prepared succesfully.
	 False, ErrorMsg -> in case of any error while preparing the response quote
'''
def processRequest(action, base_currency, quote_currency, amount):
	
	if float(amount) <= 0:
		return False, "Invalid amount"		

	#first determine what we need to check the bids or asks
	if action == "buy":
		offersToCheck = "bids"
	elif action == "sell":
		offersToCheck = "asks"
	else:
		return False, "Unknown Action type"	

	prod_type = base_currency + '-' + quote_currency	

	#Check wether the given base and quote currency belong to a valid product type or not before proceeding
	if prodListDict.get(prod_type) == None:
		prod_type = quote_currency + '-' + base_currency
		
		if prodListDict.get(prod_type) == None:
			return False, "Invalid Product type"


	#retrieve the order book for the given product type
	rVal, response = getOrderBook(prod_type)

	if rVal == False:
		return False, response	
	
	orderBook = json.loads(response)
	amountFloat = float(amount)


	Total = 0.0
	AggregatePrice = 0.0	

	if base_currency == prodListDict[prod_type]["base_currency"]:
		reverseOrderBook = False
	else:	
		reverseOrderBook = True
		
	for item in orderBook[offersToCheck][::-1]:
		size = float(item[1])
		price = float(item[0])

		if reverseOrderBook == False:
			if size <= amountFloat:
				Total += (price * size)				
				amountFloat -= size
			else:
				Total += (price * amountFloat)
				amountFloat = 0 		
			
			if amountFloat == 0:
				break;	
	
		else:	
			ratio = amountFloat/price
			
			if ratio <= size:
				Total += ratio
				amountFloat = 0
			else:
				Total += size
				amountFloat -= (price * size)
	
			if amountFloat == 0:
				break;
			

	'''
		Note : 	There might be cases where the amount we want is 10, but suppose only 5 is available. 
		    	In this case we can either execute the trade with the 5 available one or we can here
			return with an error that the given amount is not available.

			In our case we are currently taking a reference from a real life stock market scenario
			where when we buy a trade and execute it , we can get the required total quantity or the total available quantity 
			if it is less that the required quantity

	'''

	AggregatePrice = Total/(float(amount)-amountFloat)
	
	totalStr = "%.8f" % (Total)
	aggStr = "%.8f" % (AggregatePrice)
		
	#return Quote back to the user
	return True, jsonify({"total" : totalStr, "price": aggStr, "currency" : quote_currency})



#we set the route to quote to recieve post requests on it.
#additonally we have kept an extra check once we recieve the request to make sure that we have received all the required parameters in the request object

@app.route("/quote", methods=['POST'])
def getQuote():
	#cross check if the request type is json and the json obect consist of all required fields before proceeding
	#we don't require unecessary processing if the required fields are not present at all.
	if not request.json or not 'action' in request.json or not 'base_currency' in request.json or not 'quote_currency' in request.json or not 'amount' in request.json:
		abort(make_response(jsonify(message="Bad Request Type"), 400))
	else:
		requestObj = request.json 
		#print "action : %s" % (requestObj["action"])
		#print "base_currency : %s" % (requestObj["base_currency"])
		#print "quote_currency : %s" % (requestObj["quote_currency"])
		#print "amount : %s" % (requestObj["amount"])
		
		rVal, response = processRequest(requestObj["action"], requestObj["base_currency"], requestObj["quote_currency"], requestObj["amount"])

		if rVal == True:
			return response
		else:
			abort(make_response(jsonify(message=response), 400))


if __name__ == "__main__":

	if InitListofProducts() == False:
		print "Failed to initialize a list of products"
		sys.exit(1)
	else:
		print "Product list initialized successfully"


	#start the server to handle requests
	app.run()


