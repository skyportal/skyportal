#!/usr/bin/env python
#
# Return IP statistics
#

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import fire

font = {'family': 'normal', 'weight': 'bold', 'size': 24}
matplotlib.rc('font', **font)


def create_ip_chart(filenames, outfile='requests.pdf'):
    """Read nginx-access.log(s) and plot the IP addresses as pie chart.
    filenames: str
        Comma delimited list of files
    outfile: str
        Path to the output file
    """

    for ii, fn in enumerate(filenames.split(",")):
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
    plt.figure(figsize=(30, 30))
    plt.pie(
        values,
        labels=labels,
        shadow=True,
        startangle=90,
        autopct=make_autopct(values, label="Requests"),
    )
    plt.axis('equal')
    plt.savefig(outfile)
    plt.close()


if __name__ == '__main__':
    fire.Fire(create_ip_chart)
