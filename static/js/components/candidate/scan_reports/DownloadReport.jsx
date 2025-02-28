import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import React from "react";
import { useDispatch } from "react-redux";
import { fetchScanReportItem } from "../../../ducks/candidate/scan_report";
import PropTypes from "prop-types";

const DownloadReport = ({ report }) => {
  const dispatch = useDispatch();

  const downloadReport = (reportItems) => {
    const reportAsCsv = [
      `Report created by ${report.username} on ${report.created_at}\n`,
      "date, scanner, group, ZTF Name Fritz link, comment, already classified, host redshift, current mag, current age",
      ...reportItems.map((item) =>
        [
          item.saved_at,
          item.saved_by,
          item.group,
          item.obj_id,
          item.data.comment,
          item.data.already_classified,
          item.data.host_redshift,
          item.data.current_mag,
          item.data.current_age,
        ]
          .map((value) => `${value}`)
          .join(", "),
      ),
    ].join("\n");

    const blob = new Blob([reportAsCsv], { type: "text/csv;charset=utf-8;" });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Report.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownload = async () => {
    dispatch(fetchScanReportItem(report.id)).then((response) => {
      if (response.status === "success" && response.data) {
        downloadReport(response.data);
      }
    });
  };

  return (
    <IconButton onClick={handleDownload}>
      <Tooltip title="Download report">
        <CloudDownloadIcon />
      </Tooltip>
    </IconButton>
  );
};

DownloadReport.propTypes = {
  report: PropTypes.shape({
    id: PropTypes.number.isRequired,
    username: PropTypes.string.isRequired,
    created_at: PropTypes.string.isRequired,
  }),
};

export default DownloadReport;
