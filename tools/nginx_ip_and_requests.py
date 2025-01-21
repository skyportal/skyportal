#!/usr/bin/env python
#
# Return IP statistics
#

import urllib

import fire
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

font = {"family": "normal", "weight": "bold", "size": 24}
matplotlib.rc("font", **font)
matplotlib.use("Agg")


def create_ip_chart(filenames, outfile="requests.pdf", verb_to_report="ALL"):
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
            engine="python",
            usecols=[0, 4, 5, 6, 7, 8, 9, 10],
            names=[
                "ip",
                "time",
                "request",
                "status",
                "size",
                "request_length",
                "referer",
                "user_agent",
            ],
            na_values="-",
            header=None,
        )

        request_parsed = []
        indices = []
        for index, row in df.iterrows():
            request = row["request"].replace('"', "").replace("HTTP/1.1", "")
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
        df["request_parsed"] = request_parsed

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
            return f"{pct:.0f}%  ({val:d} {label})"

        return my_autopct

    df_group = df_all.groupby(["ip"])
    labels = []
    values = []
    bytes_sent = []
    requests = []
    for name, group in df_group:
        labels.append(name)
        values.append(group.count()["ip"])
        bytes_sent.append(group["size"])
        requests.append(group["request_length"])

    labels = [
        x
        for _, x in sorted(zip(values, labels), key=lambda pair: pair[0], reverse=True)
    ]
    bytes_sent = [
        x
        for _, x in sorted(
            zip(values, bytes_sent), key=lambda pair: pair[0], reverse=True
        )
    ]
    requests = [
        x
        for _, x in sorted(
            zip(values, requests), key=lambda pair: pair[0], reverse=True
        )
    ]
    values = sorted(values, reverse=True)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4, figsize=(120, 30))
    ax1.pie(
        values,
        labels=labels,
        shadow=True,
        startangle=90,
        autopct=make_autopct(values, label="Requests"),
    )
    ax1.axis("equal")
    ax1.set_title("IP Addresses")

    bins = np.logspace(-6, 3, 20)
    largest_request = -1
    largest_request_ip = ""
    for ii, (name, request) in enumerate(zip(labels, requests)):
        request_lengths = []
        for value in request:
            try:
                request_length = int(value.replace("rl=", "")) / 1e6
            except ValueError:
                continue
            request_lengths.append(request_length)
            if request_length > largest_request:
                largest_request = request_length
                largest_request_ip = name

        if ii > 10:
            continue

        hist, bin_edges = np.histogram(request_lengths, bins=bins)
        bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.0
        hist = hist / np.sum(hist)
        ax3.step(bin_centers, hist, label=name)
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.set_xlabel("Request Size [MB]", fontsize=36)
    ax3.legend(loc="upper right")

    print(f"Largest request length by {largest_request_ip} of {largest_request} MB")

    largest_bytes_sent = -1
    largest_bytes_sent_ip = ""
    for ii, (name, request) in enumerate(zip(labels, bytes_sent)):
        request_sizes = []
        for value in request:
            try:
                request_size = int(value) / 1e6
            except ValueError:
                continue
            request_sizes.append(request_size)
            if request_size > largest_bytes_sent:
                largest_bytes_sent = request_size
                largest_bytes_sent_ip = name

        if ii > 10:
            continue

        hist, bin_edges = np.histogram(request_sizes, bins=bins)
        bin_centers = (bin_edges[1:] + bin_edges[:-1]) / 2.0
        hist = hist / np.sum(hist)
        ax4.step(bin_centers, hist, label=name)
    ax4.set_xscale("log")
    ax4.set_yscale("log")
    ax4.set_xlabel("Bytes Sent [MB]", fontsize=36)
    ax4.legend(loc="upper right")

    print(f"Largest bytes sent by {largest_bytes_sent_ip} of {largest_bytes_sent} MB")

    df_group = df_all.groupby(["request_parsed"])
    labels = []
    values = []
    for name, group in df_group:
        labels.append(name)
        values.append(group.count()["request_parsed"])

    labels = [x for _, x in sorted(zip(values, labels), key=lambda pair: pair[0])]
    values = sorted(values)

    ax2.pie(
        values,
        labels=labels,
        shadow=True,
        startangle=90,
        autopct=make_autopct(values, label="Requests"),
    )
    ax2.axis("equal")
    ax2.set_title("Requests")

    plt.savefig(outfile)
    plt.close()


if __name__ == "__main__":
    fire.Fire(create_ip_chart)
