#!/bin/sh
#1
avocado run ../tests/sleeptest.py ../tests/failtest.py ../tests/synctest.py --json -
