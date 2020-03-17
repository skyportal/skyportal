#!/usr/bin/env python

import time

with open('/tmp/5_min.txt', 'a') as f:
    f.write('executed 5 min job at: ' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
