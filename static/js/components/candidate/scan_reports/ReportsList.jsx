import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import AddIcon from "@mui/icons-material/Add";
import { fetchScanReports } from "../../../ducks/candidate/scan_reports";
import ReportItems from "./ReportItems";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import GenerateReportForm from "./GenerateReportForm";
import DownloadReport from "./DownloadReport";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
});

const Fields = styled("div")({
  display: "flex",
  textAlign: "center",
});

const FieldsAndItems = styled("div")({
  borderBottom: "1px solid #d3d3d3",
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
});

const FieldsTitle = styled(Fields)({
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
  fontWeight: "bold",
  borderBottom: "1px solid grey",
});

const Field = styled("div")({
  display: "flex",
  alignItems: "center",
  padding: "0.1rem 0.5rem",
  minWidth: "200px",
  flex: 1,
});

const FieldTitle = styled(Field)({
  borderColor: "grey",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
});

const ReportsList = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const scanReports = useSelector((state) => state.scanReports);
  const [loading, setLoading] = useState(false);
  const [idReportOpen, setIdReportOpen] = useState(null);
  const [generateReportDialogOpen, setGenerateReportDialogOpen] =
    useState(false);

  useEffect(() => {
    setLoading(true);
    dispatch(
      fetchScanReports({
        numPerPage: 10,
        page: 1,
      }),
    ).then(() => setLoading(false));
  }, [dispatch]);

  const displayDate = (date) => {
    return new Date(date).toLocaleDateString("en-US", {
      hour: "2-digit",
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ marginBottom: "1rem" }}>
        <b>Candidate scanning report</b>
      </Typography>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List>
          <FieldsTitle>
            <FieldTitle>Date</FieldTitle>
            <FieldTitle>Creator</FieldTitle>
            <FieldTitle>Groups</FieldTitle>
            <FieldTitle sx={{ justifyContent: "right" }}>
              <IconButton
                name="new_report"
                onClick={() => setGenerateReportDialogOpen(true)}
              >
                <Tooltip title="Generate a report of scanned candidates">
                  <AddIcon />
                </Tooltip>
              </IconButton>
              <GenerateReportForm
                dialogOpen={generateReportDialogOpen}
                setDialogOpen={setGenerateReportDialogOpen}
              />
            </FieldTitle>
          </FieldsTitle>
          {scanReports.length > 0 ? (
            scanReports.map((scanReport) => (
              <FieldsAndItems key={scanReport.id}>
                <Fields>
                  <Field>{displayDate(scanReport.created_at)}</Field>
                  <Field>{scanReport.username}</Field>
                  <Field>
                    {scanReport.groups.map((group) => (
                      <div key={group.name}>
                        <Chip
                          label={group.name.substring(0, 15)}
                          key={group.id}
                          size="small"
                          onClick={() => navigate(`/group/${group.id}`)}
                        />
                        <br />
                      </div>
                    ))}
                  </Field>
                  <Field sx={{ justifyContent: "right" }}>
                    <IconButton
                      onClick={() =>
                        setIdReportOpen(
                          idReportOpen === scanReport.id ? null : scanReport.id,
                        )
                      }
                    >
                      {idReportOpen === scanReport.id ? (
                        <ExpandLess />
                      ) : (
                        <ExpandMore />
                      )}
                    </IconButton>
                    <DownloadReport report={scanReport} />
                  </Field>
                </Fields>
                {idReportOpen === scanReport.id && (
                  <ReportItems
                    reportId={scanReport.id}
                    isMultiGroup={scanReport.groups.length > 1}
                  />
                )}
              </FieldsAndItems>
            ))
          ) : (
            <Item
              sx={{
                display: "flex",
                justifyContent: "center",
                paddingTop: "1rem",
              }}
            >
              {loading ? (
                <CircularProgress size={24} />
              ) : (
                <Box sx={{ color: "text.secondary" }}>
                  No scanning reports found.
                </Box>
              )}
            </Item>
          )}
        </List>
      </Paper>
    </Box>
  );
};

export default ReportsList;
