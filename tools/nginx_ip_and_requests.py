#!/usr/bin/env python
#
# Return IP statistics
#

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import fire
import urllib

font = {'family': 'normal', 'weight': 'bold', 'size': 24}
matplotlib.rc('font', **font)
matplotlib.use("Agg")


def create_ip_chart(filenames, outfile='requests.pdf', verb_to_report='ALL'):
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

        request_parsed = []
        indices = []
        for index, row in df.iterrows():
            request = row['request'].replace('"', '').replace('HTTP/1.1', '')
            requestSplit = list(filter(None, request.split(" ")))
            verb = requestSplit[0]
            if verb_to_report != "ALL":
                if verb != verb_to_report:
                    continue
            indices.append(index)
            path = " ".join(requestSplit[1:])
            parsed = urllib.parse.urlparse(path)
            if "/api" in parsed.path:
                path = "/".join(parsed.path.split("/")[:3])
            else:
                path = "/".join(parsed.path.split("/")[:2])

            request_parsed.append(f"{verb} {path}")

        df = df.iloc[indices]
        df['request_parsed'] = request_parsed

        if ii == 0:
            df_all = df
        else:
            df_all = pd.concat([df_all, df])

    def make_autopct(values, label="Hours"):
        def my_autopct(pct):
            total = sum(values)
            if np.isnan(pct):
                val = 0
            else:
                val = int(round(pct * total / 100.0))
            return f'{pct:.0f}%  ({val:d} {label})'

        return my_autopct

    df_group = df_all.groupby(['ip'])
    labels = []
    values = []
    for name, group in df_group:
        labels.append(name)
        values.append(group.count()['ip'])

    labels = [x for _, x in sorted(zip(values, labels), key=lambda pair: pair[0])]
    values = sorted(values)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(60, 30))
    ax1.pie(
        values,
        labels=labels,
        shadow=True,
        startangle=90,
        autopct=make_autopct(values, label="Requests"),
    )
    ax1.axis('equal')
    ax1.set_title('IP Addresses')

    df_group = df_all.groupby(['request_parsed'])
    labels = []
    values = []
    for name, group in df_group:
        labels.append(name)
        values.append(group.count()['request_parsed'])

    labels = [x for _, x in sorted(zip(values, labels), key=lambda pair: pair[0])]
    values = sorted(values)

    ax2.pie(
        values,
        labels=labels,
        shadow=True,
        startangle=90,
        autopct=make_autopct(values, label="Requests"),
    )
    ax2.axis('equal')
    ax2.set_title('Requests')

    plt.savefig(outfile)
    plt.close()


if __name__ == '__main__':
    fire.Fire(create_ip_chart)
