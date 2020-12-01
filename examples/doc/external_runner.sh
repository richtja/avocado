#!/bin/sh
#1
echo "exit 0" > /tmp/pass
echo "exit 1" > /tmp/fail
avocado run --external-runner=/bin/sh /tmp/pass /tmp/fail
