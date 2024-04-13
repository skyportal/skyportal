function downloadPhotometryToCsv(photometry_data, source_id) {
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
    downloadCSVFile(csv_data, source_id);
}

function downloadTableToCSV(type) {
    let csv_data = [];
    let table = document.getElementById(type);
    let rows = table.querySelectorAll("tr");
    for (let i = 0; i < rows.length; i++) {
        let cols = rows[i].querySelectorAll("td,th");
        let csv_row = [];
        for (let j = 0; j < cols.length; j++) {
            if (cols[j].querySelector("a")) {
                csv_row.push(cols[j].querySelector("a").text);
            } else if(!cols[j].querySelector("button")) {
                csv_row.push(cols[j].innerHTML);
            }
        }
        csv_data.push(csv_row.join(","));
    }
    csv_data = csv_data.join("\n");
    downloadCSVFile(csv_data, type);
}

function downloadCSVFile(csv_data, file_name) {
    const CSVFile = new Blob([csv_data], { type: "text/csv" });
    const temp_link = document.createElement("a");
    temp_link.download = file_name + ".csv";
    temp_link.href = window.URL.createObjectURL(CSVFile);
    temp_link.style.display = "none";
    document.body.appendChild(temp_link);
    temp_link.click();
    document.body.removeChild(temp_link);
}