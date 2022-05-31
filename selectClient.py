import socket
import pickle
import random

class item:
    def __init__(self,descr,price,id):
        self.descr=descr
        self.price=price
        self.clientId = None
        self.id = id
    def setBid(self,price):
        self.price = price
    def printHeader(self):
        print("ID\tDescr\tPrice\tHighest Bidder")
    def printInfo(self):
        print(f"{self.id}\t{self.descr}\t{self.price}\tClient {self.clientId}")

class clientCatalog:
    def __init__(self,inputFile):
        self.items = {}
        f = open(inputFile,"r")
        f.readline() # skip header
        curItem = f.readline()
        while(curItem):
            descr, _, price = curItem.split()
            randMult = random.random() + 1.5 # [0 - 1) + 1
            self.items[descr] = round(int(price) * randMult,2)
            curItem = f.readline()
        print("Maximum Prices")
        for x in self.items:
            print(f"{x}: {self.items[x]}")
    def getItemMaxBid(self, descr):
        return self.items[descr]

cat = clientCatalog("input.txt")

#myIncreaseTest = (random.randrange(1,20))/100 + 1
#print(myIncreaseTest)

server_address = ('10.20.82.161',8080)

#Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
print ('connecting to %s port %s' % server_address)
sock.connect(server_address)

# client id assigned by server
#clientId = int.from_bytes(sock.recv(1024),'big')
clientId = pickle.loads(sock.recv(1024))
print("This client was given id",clientId)

curItemId = -1

wonItems = []


while True:

    # Read response
    data = sock.recv(1024)
    if data:
        curItem = pickle.loads(data)
        if(not curItem.id==curItemId):
            # new item
            # print("New Item")
            curItem.printHeader()
            curItemId = curItem.id

        curItem.printInfo()

        #check if this client is item winner
        if(curItem.clientId==clientId):
            #record item as won
            wonItems.append(curItem)
            print("Auction won\n")

        # check to see if item price is already above client's pre-set maximum bid
        elif(curItem.price > cat.getItemMaxBid(curItem.descr)):
            
            # update display that item price is above pre-set maximum
            print("Item price above pre-set maximum bid: {}.\n"
            .format(cat.getItemMaxBid(curItem.descr)))

            # alert server that client will not bid anymore on this item
            curItem.setBid(-1)
            sock.send(pickle.dumps(curItem))

        elif(random.randrange(0,9)<3):
            # represent 30% chance to "not bid"
            print("Not bidding (as per 30% chance preference)")

            # send nothing to server

        else:
            # calculate a new bid. take minimum of it and pre-set maximum

            # increase bid by 1% to 20%
            increase = (random.randrange(1,20)/100) + 1 # [1.01 - 1.20]
            potentialBid = curItem.price * increase

            # ensure new bid is less than pre-set maximum bid
            bid = round(min(potentialBid, cat.getItemMaxBid(curItem.descr)),2)

            # update display
            print("Bidding",bid)

            # use item object to communicate new bid
            curItem.setBid(bid)

            # pickle item object to send through socket
            pItem = pickle.dumps(curItem)

            # send pickled item object through socket
            sock.send(pItem)

    else:
        print ('closing socket', sock.getsockname())
        sock.close()