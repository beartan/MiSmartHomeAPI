BASE_URL=http://localhost:8000

NAME=Lamp
LOCALIP='192.168.31.245'
TOKEN='eb6ce266e5a6c25cbc2515471634d2be'
DID='235388260'

# PUT - Add a device.
curl -X PUT -d "name=${NAME}&localip=${LOCALIP}&token=${TOKEN}" ${BASE_URL}/${DID}

# GET - List terminals(include devices and sensors) infomation.
curl ${BASE_URL}

# POST - Given instructions, control device(Default switch on and off status).
curl -d "" ${BASE_URL}/${DID}
