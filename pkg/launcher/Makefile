CC = gcc
CFLAGS = -g -Wall
STRIP = strip

default: bitmask

bitmask.o: bitmask-launcher.c
	$(CC) $(CFLAGS) -c bitmask-launcher.c -o bitmask.o

bitmask: bitmask.o
	$(CC) bitmask.o -o bitmask
	$(STRIP) bitmask
clean:
	-rm -f bitmask.o
	-rm -f bitmask
