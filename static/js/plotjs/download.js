/* eslint-disable */
function table_to_csv(source, write_header) {
  const columns = [
    "mjd",
    "filter",
    "mag",
    "magerr",
    "flux",
    "fluxerr",
    "zp",
    "magsys",
    "lim_mag",
    "stacked",
  ];
  const nrows = source.get_length();
  const lines = [];

  if (write_header) {
    let now = new Date();
    lines.push(`# source: "objname" downloaded at: ${now.toISOString()} UTC`);
    lines.push(columns.join(","));
  }

  for (let i = 0; i < nrows; i++) {
    const row = [];
    for (let j = 0; j < columns.length; j++) {
      const column = columns[j];
      try {
        row.push(source.data[column][i].toString());
      } catch (error) {
        if (column === "zp") {
          row.push(default_zp);
        } else if (column === "magsys") {
          row.push("ab");
        } else {
          throw error;
        }
      }
    }
    lines.push(row.join(","));
  }

  return lines.join("\n").concat("\n");
}

const filename = "objname.csv";
let filetext = "";
for (let i = 0; i < n_labels; i++) {
  const write_header = i === 0;
  filetext += table_to_csv(eval(`bold${i}`), write_header);
}
const blob = new Blob([filetext], { type: "text/csv;charset=utf-8;" });

// addresses IE
if (navigator.msSaveBlob) {
  navigator.msSaveBlob(blob, filename);
} else {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.target = "_blank";
  link.style.visibility = "hidden";
  link.dispatchEvent(new MouseEvent("click"));
}
