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
    const reportData = {
      created_by: report.username,
      created_at: report.created_at,
      items: reportItems,
    };

    const blob = new Blob([JSON.stringify(reportData)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Report.json";
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
