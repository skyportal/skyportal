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
matplotlib.use("Agg")


def create_ip_chart(filenames, outfile='requests.pdf'):
    """Read nginx-access.log(s) and plot the IP addresses as pie chart.
    filenames: str
        Comma delimited list of files
    outfile: str
        Path to the output file
    """

    verbs = ['GET', 'PUT', 'POST', 'PATCH', 'PUT', 'HEAD', 'DELETE']
    endpoints = [
        '/index',
        '/baselayer',
        '/static',
        '/source',
        '/complete',
        '/owa',
        '/api/allocation',
        '/api/listing',
        '/api/candidates',
        '/api/groups',
        '/api/sources',
        '/api/source',
        '/api/filters',
        '/api/instrument',
        '/api/allocations',
        '/api/internal',
        '/api/telescope',
        '/api/tns_robot',
        '/api/tns_info',
        '/api/archive',
        '/api/alerts_aux',
        '/api/spectrum',
        '/api/newsfeed',
        '/api/alerts_cutouts',
        '/api/streams',
        '/api/observing_run',
        '/api/shifts',
        '/api/default_observation_plan',
        '/api/photometry',
        '/api/observation',
        '/api/followup_request',
        '/api/galaxy_catalog',
        '/api/user',
        '/api/gcn_event',
        '/api/spectra',
        '/api/alerts',
        '/api/roles',
    ]

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

        for verb in verbs:
            for endpoint in endpoints:
                df['request'][
                    df['request'].str.contains(f"{verb} {endpoint}", case=False)
                ] = f"{verb} {endpoint}"

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

    df_group = df_all.groupby(['request'])
    labels = []
    values = []
    for name, group in df_group:
        labels.append(name)
        values.append(group.count()['request'])

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
