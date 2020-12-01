#!/bin/sh
#0
avocado run sleeptest.py synctest.py --xunit - --json /tmp/result.json
