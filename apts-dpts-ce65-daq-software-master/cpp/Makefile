CC=g++
#GIT_VERSION:=$(shell git describe --dirty --always) # -DVERSION=\"$(GIT_VERSION)\"
CFLAGS= -pipe -fPIC -g -pg -std=c++0x
LINKFLAGS=-lusb-1.0
OBJECT= test
LIBRARY=libpalpidefs.so
CLASS=  USB.cpp TDaqboard.cpp TTestsetup.cpp
OBJS = $(CLASS:.cpp=.o)

all:	test

$(OBJECT):	$(OBJS) test.cpp
	$(CC) -o $@ $(OBJS) $(CFLAGS) test.cpp $(LINKFLAGS)

%.o: %.cpp %.h
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -rf *.o $(OBJECT) $(LIBRARY)
	rm -rf test
