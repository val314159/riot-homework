call: clean all
all:
	./price_history_server.py 6666
docs:
	pydoc3  price_history_server
clean:
	rm -fr *~ __pycache__
	ls -la
install:
	pip3 install -r requirements.txt
	cp price_history_server.py /usr/local/bin

