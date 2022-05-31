import select
import socket
import time
import pickle

# class to contain each client's information: connection, id, current item, prices
class client:
    def __init__(self, connection, id):
        self.connection = connection
        self.id = id
        self.bid=None
        self.itemId = None
    def setBid(self, bid, itemId):
        if self.itemId==itemId:
            self.bid = bid
        else:
            print("Client",self.id,"attempted to bid on item", itemId,", but",
            "current item is set to", self.itemId)
            return False
    def setItemId(self,itemId):
        self.itemId = itemId

class item:
    def __init__(self,descr,price,id):
        self.descr=descr
        self.price=price
        self.clientId = None
        self.id = id
    # sets highest bidder and bid amount for item.  returns false if no update needed
    def setHighestBidder(self,clientId,price):
        if(self.clientId==clientId and self.price==price):
            return False
        else:
            self.clientId = clientId
            self.price = price
            return True
    def printHeader(self):
        print("ID\tDescr\tPrice\tHighest Bidder")
    def printInfo(self):
        print(f"{self.id}\t{self.descr}\t{self.price}\tClient {self.clientId}")

class catalog:

    curItemList = 0
    curItemIndex = 0

    def __init__(self,inputFile):
        self.items = []
        # read file with items information
        f = open(inputFile,"r")
        f.readline() #skip heading
        curItem = f.readline()
        itemId = 0
        while(curItem): #will stop on empty string (end of file)
            descr, quantity, price = curItem.split() #description, quantity, price
            quantity = int(quantity) #convert string to integer
            price = int(price) #convert string to integer
            itemList = []
            for x in range(0,quantity):
                itemList.append(item(descr,price,itemId))
                itemId += 1
            for x in range(0,len(itemList)):
                itemList[x].printInfo()
            curItem = f.readline()
            self.items.append(itemList)

    def getCurItem(self):
        return self.items[self.curItemList][self.curItemIndex]

    def getNextItem(self):
        self.curItemIndex += 1
        if(not self.curItemIndex < len(self.items[self.curItemList])):
            self.curItemList += 1
            if(not self.curItemList < len(self.items)):
                return False
            else:
                self.curItemIndex = 0
        return self.items[self.curItemList][self.curItemIndex]
    
    def print(self):
        for itemList in self.items:
            for item in itemList:
                item.printInfo()

# prints out information on all connected clients
def clientsInfo(clients):
    print("-- Clients Information --")
    for c in clients:
        print("Client ID:",clients[c].id)

# track number of connected clients
clientCnt = 0

# dictionary to hold each client object by its connection information
clients = {}

# Create a TCP/IP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

# Bind socket to port
server_address = ('10.20.82.161',8080)
print ('starting up on %s port %s' % server_address)
server.bind(server_address)

#Listen for incoming connections
server.listen(5)

#Sockets from which we expect to read
inputs = [server]

#Sockets to which we expect to write
outputs = []

# Store input list in memory
cat = catalog("input.txt")

# set first item
curItem = cat.getCurItem()
# update display
print("\nNew Auction Item")
curItem.printHeader()
curItem.printInfo()

# time bidding ends
stop = None

# bidding time (seconds)
bidTime = 5


while inputs:

    # Wait for at least one of the sockets to be ready for processing
    # print('\nwaiting for the next event')
    readable, writable, exceptional = select.select(inputs,outputs,inputs)

    # Handle inputs
    for s in readable:

        # new client connection
        if s is server:
            # A 'readable' server socket is ready to accept a connection
            connection, client_address = s.accept()
            print('\nnew connection from', client_address)
            # print('connection: ', connection)
            connection.setblocking(0)
            inputs.append(connection)

            # add output channel
            if connection not in outputs:
                outputs.append(connection)

            #send client its id
            connection.send(pickle.dumps(clientCnt)) 

            # create client object
            c = client(connection,clientCnt)
            c.setItemId(curItem.id)
            clientCnt+=1

            # add client object to list of clients
            clients[connection] = c

            print("Connected Clients Count:", len(clients),"\n")
            #clientsInfo(clients)

            # restart bidding window
            stop = time.time() + bidTime
        
        # bid from client
        else:
            # print("\nReceived bid from client",clients[s].id)
            data = s.recv(1024)
            if data:
                # A readable client socket has data
                # print('received "%s" from %s' % (data, s.getpeername()))

                clientItem = pickle.loads(data)
                if(not curItem.id == clientItem.id):
                    #client somehow bid on wrong item.  ignore
                    print("Client some how bid on wrong item.  Ignoring.")
                
                # check if client made real bid.  -1 means it's out of auction.
                elif(clientItem.price==-1):
                    #print("Client",clients[s].id,"will no longer bid on this item.")
                    if s in outputs:
                        outputs.remove(s)
                    if s in writable:
                        writable.remove(s)

                else:
                    # set client bid
                    clients[s].setBid(clientItem.price,clientItem.id)
                    # restart bidding timer
                    stop = time.time() + bidTime

                    
                    print("Client",clients[s].id,"bid",clients[s].bid)
            else:
                # Interpret empty result as closed connection
                print ('closing', client_address, 'after reading no data')
                if s in outputs:
                    outputs.remove(s)
                if s in writable:
                    writable.remove(s)
                
                # Stop listening for input on the connection
                inputs.remove(s)
                
                s.close()

    # check if bidding window is over
    if(time.time()>=stop):
        # notify winner of auction, choose new item

        # notify display
        print("Client",curItem.clientId,"won",curItem.descr,f"for ${curItem.price}")

        # find winning client's socket and send item information
        # winning client recognizes win through clientId match
        for c in clients:
            if (clients[c].id == curItem.clientId):
                # send winner item
                c.send(pickle.dumps(curItem))

        # get next item
        curItem = cat.getNextItem()

        # no more items left.  break while loop to end program
        if(not curItem):
            break

        # notify display
        print("\nNew Auction Item")
        curItem.printHeader()
        curItem.printInfo()



        # reset all clients to default bidding-start state
        for c in clients:
            # set each client to new item id.  
            # this ensure late bids go to correct items.
            clients[c].setItemId(curItem.id)

            # put all sockets back into outputs list
            if c not in outputs:
                outputs.append(c)

    else:
        # determine current highest bidder, reset bidding timer

        # notify display
        # print("Calculating Current Highest Bidder. Client Count:", len(clients))


        highestBidder = curItem.clientId
        curHighestBid = curItem.price

        for c in clients:
            # check if client made a bid, and if bid is highest
            if(clients[c].bid and clients[c].bid > curHighestBid):
                highestBidder = clients[c].id
                curHighestBid = clients[c].bid

            #set all client bids back to undefined
            clients[c].bid = None
        
        # record which client is highest bidder, and bid amount
        if(curItem.setHighestBidder(highestBidder,curHighestBid)):
            print(f"Highest Bid: Client {curItem.clientId}\t${curItem.price}")

    #pickle auction object
    pItem = pickle.dumps(curItem)

    # Handle outputs
    for s in writable:
        if(not clients[s].id == curItem.clientId):
            s.send(pItem)

        #try:
            # next_msg = message_queues[s].get_nowait()
        #except queue.Empty:
            # No messages waiting so stop checking for writability
        #    print('output queue for', s.getpeername(), 'is empty')
        #    outputs.remove(s)
        #else:
        #    print('sending "%s" to %s' % (next_msg, s.getpeername()))
        #    s.send(next_msg)
    
    # Handle 'exceptional conditions'
    for s in exceptional:
        print ('handling exceptional condition for', s.getpeername())
        # Stop listening for input on the connection
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()

    # sleep server to let clients catch up
    time.sleep(3)

# print out all items' information: descr, winner, winning bid amount
cat.print()