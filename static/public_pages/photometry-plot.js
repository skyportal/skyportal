const filter_mapper = {
    ztfg: "green",
    ztfr: "red",
    ztfi: "orange",
};

function filter2color(filter) {
    return filter_mapper[filter] || "blue";
}

function ModifiedJulianDateFromUnixTime(t) {
    return t / 86400000 + 40587;
}

function ModifiedJulianDateNow() {
    return ModifiedJulianDateFromUnixTime(new Date().getTime());
}

function plot_lc(photometry_data) {
    const photometry = JSON.parse(photometry_data);
    const now = ModifiedJulianDateNow();
    let names_already_seen = [];
    let plot_data = [];

    photometry.forEach((element) => {
        let name = `${element["instrument_name"]}/${element["filter"]}`;
        if (element["origin"] !== "None") {
            name = `${name}/${element["origin"]}`;
        }
        let data = {
            x: [now - element["mjd"]],
            y:
                element["mag"] === null
                    ? [element["limiting_mag"]]
                    : [element["mag"]],
            name: name,
            error_y: {
                type: "data",
                array: [element["magerr"]],
                visible: true,
                color: filter2color(element["filter"]),
                width: 2,
                thickness: 0.8,
                opacity: 0.5,
            },
            legendgroup: name,
            marker: {
                symbol: element["mag"] === null ? "triangle-down" : "circle",
                color: filter2color(element["filter"]),
                opacity: 0.8,
                size: 8,
            },
            line: {
                color: filter2color(element["filter"]),
                width: 2,
                opacity: 0.8,
            },
            mode: "markers+lines",
            // use a hover template to display:
            // - mjd
            // - mag
            // - magerr
            // - filter
            // - limiting_mag
            // - instrument_id
            text: `mjd: ${element["mjd"].toFixed(6)}<br>mag: ${
                element["mag"] ? element["mag"].toFixed(4) : element["mag"]
            }<br>magerr: ${
                element["magerr"]
                    ? element["magerr"].toFixed(4)
                    : element["magerr"]
            }<br>filter: ${element["filter"]}<br>limmag: ${
                element["limiting_mag"]
                    ? element["limiting_mag"].toFixed(4)
                    : element["limiting_mag"]
            }<br>instrument: ${element["instrument_name"]}`,
        };
        data["showlegend"] = !names_already_seen.includes(name);
        plot_data.push(data);
        names_already_seen.push(name);
    });
    let layout = {
        autosize: true,
        xaxis: {title: "Days ago", autorange: "reversed"},
        yaxis: {title: "AB Mag", autorange: "reversed"},
        margin: {l: 50, r: 50, b: 30, t: 30, pad: 1},
    };
    let config = {responsive: true};

    Plotly.newPlot(
        document.getElementById("photometryPlot"),
        plot_data,
        layout,
        config
    );
}

function photometryToCsv(photometry_data) {
    const photometry = JSON.parse(photometry_data);
    let csv_data = [];
    let csv_row = [];
    csv_row.push("mjd");
    csv_row.push("mag");
    csv_row.push("magerr");
    csv_row.push("filter");
    csv_row.push("limiting_mag");
    csv_row.push("instrument_id");
    csv_row.push("instrument_name");
    csv_row.push("origin");
    csv_data.push(csv_row.join(","));
    photometry.forEach((element) => {
        let csv_row = [];
        csv_row.push(element["mjd"]);
        csv_row.push(element["mag"]);
        csv_row.push(element["magerr"]);
        csv_row.push(element["filter"]);
        csv_row.push(element["limiting_mag"]);
        csv_row.push(element["instrument_id"]);
        csv_row.push(element["instrument_name"]);
        csv_row.push(element["origin"]);
        csv_data.push(csv_row.join(","));
    });
    csv_data = csv_data.join("\n");
    downloadCSVFile(id, csv_data);
}