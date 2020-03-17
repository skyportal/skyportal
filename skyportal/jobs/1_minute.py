#!/usr/bin/env python

import time

with open('/tmp/1_min.txt', 'a') as f:
    f.write('executed 1 min job at: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
