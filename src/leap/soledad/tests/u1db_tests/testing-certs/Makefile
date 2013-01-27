CATOP=./demoCA
ORIG_CONF=/usr/lib/ssl/openssl.cnf
ELEVEN_YEARS=-days 4015

init:
	cp $(ORIG_CONF) ca.conf
	install -d $(CATOP)
	install -d $(CATOP)/certs
	install -d $(CATOP)/crl
	install -d $(CATOP)/newcerts
	install -d $(CATOP)/private
	touch $(CATOP)/index.txt
	echo 01>$(CATOP)/crlnumber
	@echo '**** Making CA certificate ...'
	openssl req -nodes -new \
	 	-newkey rsa -keyout $(CATOP)/private/cakey.pem \
		-out $(CATOP)/careq.pem \
		-multivalue-rdn \
        -subj "/C=UK/ST=-/O=u1db LOCAL TESTING ONLY, DO NO TRUST/CN=u1db testing CA"
	openssl ca -config ./ca.conf -create_serial \
		-out $(CATOP)/cacert.pem $(ELEVEN_YEARS) -batch \
		-keyfile $(CATOP)/private/cakey.pem -selfsign \
		-extensions v3_ca -infiles $(CATOP)/careq.pem

pems:
	cp ./demoCA/cacert.pem .
	openssl req -new -config ca.conf \
		-multivalue-rdn \
	-subj "/O=u1db LOCAL TESTING ONLY, DO NOT TRUST/CN=localhost" \
		-nodes -keyout testing.key -out newreq.pem $(ELEVEN_YEARS)
	openssl ca -batch -config ./ca.conf $(ELEVEN_YEARS) \
		-policy policy_anything \
		-out testing.cert -infiles newreq.pem

.PHONY: init pems
