import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import AddIcon from "@mui/icons-material/Add";
import { fetchScanReports } from "../../../ducks/candidate/scan_reports";
import ReportItems from "./ReportItems";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import GenerateReportForm from "./GenerateReportForm";

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
  const scanReports = useSelector((state) => state.scanReports);
  const [loading, setLoading] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
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
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ marginBottom: "1rem" }}>
        <b>Candidate scan report</b>
      </Typography>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List>
          <FieldsTitle>
            <FieldTitle>Date</FieldTitle>
            <FieldTitle>Creator</FieldTitle>
            <FieldTitle sx={{ flex: 1, justifyContent: "right" }}>
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
                  <Field>{scanReport.creator.username}</Field>
                  <Field
                    sx={{ flex: 1, justifyContent: "right", cursor: "pointer" }}
                    onClick={() => setReportOpen(!reportOpen)}
                  >
                    <IconButton onClick={() => setReportOpen(!reportOpen)}>
                      {reportOpen ? <ExpandLess /> : <ExpandMore />}
                    </IconButton>
                  </Field>
                </Fields>
                {reportOpen && <ReportItems reportId={scanReport.id} />}
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
                  No scan reports found.
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
