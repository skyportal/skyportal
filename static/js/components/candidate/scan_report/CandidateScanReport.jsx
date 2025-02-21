import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import EditIcon from "@mui/icons-material/Edit";
import { Link } from "react-router-dom";
import { fetchCandidatesScanReports } from "../../../ducks/candidate/candidate_scan_report";
import EditReportCandidateForm from "./EditReportCandidateForm";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
});

const Field = styled("div")({
  flex: 1,
  borderRight: "1px solid #d3d3d3",
  fontSize: "0.8rem",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  padding: "0.1rem 0.2rem",
  minWidth: "120px",
});

const FieldTitle = styled(Field)({
  borderColor: "grey",
});

const CandidateScanReport = () => {
  const dispatch = useDispatch();
  const candidatesScan = useSelector((state) => state.candidatesScanReports);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reportCandidateToEdit, setReportCandidateToEdit] = useState(null);

  useEffect(() => {
    setLoading(true);
    dispatch(
      fetchCandidatesScanReports({
        rows: 10,
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

  const boolToStr = (condition) => {
    if (condition === null) return "";
    return condition ? "True" : "False";
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ marginBottom: "1rem" }}>
        <b>Candidate scan report</b>
      </Typography>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List>
          <Item
            sx={{
              fontWeight: "bold",
              borderBottom: "1px solid grey",
            }}
          >
            <FieldTitle>date</FieldTitle>
            <FieldTitle>scanner</FieldTitle>
            <FieldTitle sx={{ flex: 2 }}>ZTF Name Fritz link</FieldTitle>
            <FieldTitle sx={{ flex: 3 }}>comment</FieldTitle>
            <FieldTitle>already classified</FieldTitle>
            <FieldTitle>host redshift</FieldTitle>
            <FieldTitle>current mag</FieldTitle>
            <FieldTitle>current age</FieldTitle>
            <FieldTitle>forced photometry requested</FieldTitle>
            <FieldTitle sx={{ borderRight: "none" }}></FieldTitle>
          </Item>
          {candidatesScan.length > 0 ? (
            candidatesScan.map((candidateScan) => (
              <Item
                key={candidateScan.id}
                sx={{ borderBottom: "1px solid #d3d3d3" }}
              >
                <Field>{displayDate(candidateScan.date)}</Field>
                <Field>{candidateScan.scanner}</Field>
                <Field sx={{ flex: 2 }}>
                  <Link
                    to={`/source/${candidateScan.obj_id}`}
                    role="link"
                    target="_blank"
                  >
                    {candidateScan.obj_id}
                  </Link>
                </Field>
                <Field sx={{ flex: 3 }}>{candidateScan.comment}</Field>
                <Field>{boolToStr(candidateScan.already_classified)}</Field>
                <Field>{candidateScan.host_redshift}</Field>
                <Field>{candidateScan.current_mag}</Field>
                <Field>{candidateScan.current_age}</Field>
                <Field>
                  {boolToStr(candidateScan.forced_photometry_requested)}
                </Field>
                <Field sx={{ borderRight: "none" }}>
                  <Button
                    onClick={() => {
                      setReportCandidateToEdit(candidateScan);
                      setDialogOpen(true);
                    }}
                  >
                    <EditIcon color="primary" fontSize="small" />
                  </Button>
                </Field>
              </Item>
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
                  No candidate saved to the report yet
                </Box>
              )}
            </Item>
          )}
        </List>
      </Paper>
      {reportCandidateToEdit && (
        <EditReportCandidateForm
          dialogOpen={dialogOpen}
          setDialogOpen={setDialogOpen}
          reportCandidateToEdit={reportCandidateToEdit}
          setReportCandidateToEdit={setReportCandidateToEdit}
        />
      )}
    </Box>
  );
};

CandidateScanReport.propTypes = {
  scanList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      date: PropTypes.string.isRequired,
      scanner: PropTypes.string.isRequired,
      obj_id: PropTypes.string.isRequired,
      comment: PropTypes.string.isRequired,
      already_classified: PropTypes.bool,
      host_redshift: PropTypes.number,
      current_mag: PropTypes.number,
      current_age: PropTypes.number,
      forced_photometry_requested: PropTypes.bool,
    }),
  ),
};

export default CandidateScanReport;
