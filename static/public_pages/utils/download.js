function downloadFile(data, file_name, extension = null) {
  const file = new Blob([data], { type: `text/${extension || "plain"}` });
  const temp_link = document.createElement("a");
  temp_link.download = `${file_name}`;
  temp_link.href = window.URL.createObjectURL(file);
  temp_link.style.display = "none";
  document.body.appendChild(temp_link);
  temp_link.click();
  document.body.removeChild(temp_link);
}

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
  downloadFile(csv_data, type, "csv");
}

function downloadPhotometryToCsv(data, filename) {
  const photometry = JSON.parse(data);

  const headers = [
    "mjd",
    "mag",
    "magerr",
    "filter",
    "limiting_mag",
    "instrument_id",
    "instrument_name",
    "origin",
    "notes",
  ];
  const isFloat = (x) =>
    typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

  const csv_data = [
    headers.join(","),
    ...photometry.map((element) =>
      headers
        .map((header) => {
          if (isFloat(element[header])) {
            return element[header].toFixed(header === "mjd" ? 8 : 2);
          }
          return element[header];
        })
        .join(","),
    ),
  ].join("\n");
  downloadFile(csv_data, filename, "csv");
}

function downloadSpectroscopy(data, filename, isOriginalFile) {
  if (JSON.parse(isOriginalFile)) {
    downloadFile(data, filename, null);
    return;
  }

  const spectroscopy = JSON.parse(data);
  const headers = [
    "wavelength",
    "flux",
    ...(spectroscopy.fluxerr ? ["fluxerr"] : []),
  ];
  const processFilename = `${filename}_${spectroscopy.instrument}`;
  const csv_data = [
    headers.join(","),
    ...spectroscopy.wavelengths?.map((wave, i) => {
      let line = `${wave},${spectroscopy.fluxes[i]}`;
      if (spectroscopy.fluxerr) {
        return `${line},${spectroscopy.fluxerr[i]}`;
      }
      return line;
    }),
  ].join("\n");
  downloadFile(csv_data, processFilename, "csv");
}
