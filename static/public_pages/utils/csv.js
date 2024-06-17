function downloadCSVFile(csv_data, file_name) {
  const CSVFile = new Blob([csv_data], { type: "text/csv" });
  const temp_link = document.createElement("a");
  temp_link.download = `${file_name}.csv`;
  temp_link.href = window.URL.createObjectURL(CSVFile);
  temp_link.style.display = "none";
  document.body.appendChild(temp_link);
  temp_link.click();
  document.body.removeChild(temp_link);
}

/* eslint-disable no-unused-vars */
function downloadPhotometryToCsv(photometry_data, source_id) {
  const photometry = JSON.parse(photometry_data);

  const headers = [
    "mjd",
    "mag",
    "magerr",
    "filter",
    "limiting_mag",
    "instrument_id",
    "instrument_name",
    "origin",
  ];
  const csv_data = [
    headers.join(","),
    ...photometry.map((element) =>
      headers.map((header) => element[header]).join(","),
    ),
  ].join("\n");
  downloadCSVFile(csv_data, source_id);
}

/* eslint-disable no-unused-vars */
function downloadTableToCSV(type) {
  let csv_data = [];
  const table = document.getElementById(type);
  const rows = Array.from(table.querySelectorAll("tr"));
  rows.forEach((row) => {
    const cols = Array.from(row.querySelectorAll("td,th"));
    const csv_row = [];
    cols.forEach((col) => {
      if (col.querySelector("a")) {
        csv_row.push(col.querySelector("a").text.trim());
      } else if (!col.querySelector("button")) {
        csv_row.push(col.innerHTML.trim());
      }
    });
    csv_data.push(csv_row.join(","));
  });
  csv_data = csv_data.join("\n");
  downloadCSVFile(csv_data, type);
}
