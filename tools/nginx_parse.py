#!/usr/bin/env python
#
# Return IP statistics
#

import sys
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

font = {'family': 'normal', 'weight': 'bold', 'size': 24}
matplotlib.rc('font', **font)

if len(sys.argv) < 2:
    print("Usage: nginx_parse.py filename0.log filename1.log ...")
    sys.exit(1)


for ii, fn in enumerate(sys.argv[1:]):
    df = pd.read_csv(
        fn,
        sep=r'\s(?=(?:[^"]*"[^"]*")*[^"]*$)(?![^\[]*\])',
        engine='python',
        usecols=[0, 4, 5, 6, 7, 8, 9],
        names=['ip', 'time', 'request', 'status', 'size', 'referer', 'user_agent'],
        na_values='-',
        header=None,
    )
    if ii == 0:
        df_all = df
    else:
        df_all = pd.concat([df_all, df])

df_group = df_all.groupby(['ip'])
labels = []
values = []
for name, group in df_group:
    labels.append(name)
    values.append(group.count()['ip'])

labels = [x for _, x in sorted(zip(values, labels), key=lambda pair: pair[0])]
values = sorted(values)


def make_autopct(values, label="Hours"):
    def my_autopct(pct):
        total = sum(values)
        if np.isnan(pct):
            val = 0
        else:
            val = int(round(pct * total / 100.0))
        return f'{pct:.0f}%  ({val:d} {label})'

    return my_autopct


matplotlib.use("Agg")
fig = plt.figure(figsize=(30, 30))
plt.pie(
    values,
    labels=labels,
    shadow=True,
    startangle=90,
    autopct=make_autopct(values, label="Requests"),
)
plt.axis('equal')
plt.savefig('requests.pdf')
plt.close()
