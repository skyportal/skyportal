import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import { scanReportItemApi } from "../../../ducks/candidate/scan_report";
import { useAppDispatch } from "../../../types/hooks";

interface DownloadReportProps {
  report: {
    id: number;
    username: string;
    created_at: string;
    [key: string]: any;
  };
}

const DownloadReport = ({ report }: DownloadReportProps) => {
  const dispatch = useAppDispatch();

  const downloadReport = (reportItems: any[]) => {
    const reportData = {
      report_id: report.id,
      created_by: report.username,
      created_at: report.created_at,
      number_of_items: reportItems.length,
      items: reportItems.map(
        ({ id, scan_report_id, created_at, ...rest }: any) => rest,
      ),
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
    try {
      const reportItems = await dispatch(
        scanReportItemApi.endpoints.getScanReportItems.initiate(report.id),
      ).unwrap();
      if (reportItems) {
        downloadReport(reportItems as any[]);
      }
    } catch {
      // error notification already fired by the base query
    }
  };

  return (
    <IconButton onClick={handleDownload}>
      <Tooltip title="Download report">
        <CloudDownloadIcon />
      </Tooltip>
    </IconButton>
  );
};

export default DownloadReport;
