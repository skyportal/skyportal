import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import { useDispatch } from "react-redux";
import { fetchCandidatesScanReport } from "../../../ducks/candidate/candidate_scan_report";
import CircularProgress from "@mui/material/CircularProgress";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
  paddingBottom: "0.5rem",
  marginBottom: "0.5rem",
});

const FieldTitle = styled("div")({
  flex: 1,
  borderRight: "1px solid grey",
  fontSize: "0.9rem",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  paddingY: "0.1rem",
  overflow: "auto",
});

const Field = styled("div")({
  flex: 1,
  borderRight: "1px solid #d3d3d3",
  fontSize: "0.8rem",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  paddingY: "0.1rem",
});

const CandidateScanReport = () => {
  const dispatch = useDispatch();
  const [candidatesScan, setCandidatesScan] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    dispatch(
      fetchCandidatesScanReport({
        rows: 10,
        page: 1,
      }),
    ).then((res) => {
      setLoading(false);
      setCandidatesScan(res.data);
    });
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
      <Typography variant="h5" sx={{ marginBottom: "0.5rem" }}>
        <b>Candidate scan report</b>
      </Typography>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List sx={{ minWidth: "1800px" }}>
          <Item
            sx={{
              fontWeight: "bold",
              borderBottom: "1px solid grey",
            }}
          >
            <FieldTitle>date</FieldTitle>
            <FieldTitle>scanner</FieldTitle>
            <FieldTitle sx={{ flex: 2 }}>candidate</FieldTitle>
            <FieldTitle sx={{ flex: 3 }}>comment</FieldTitle>
            <FieldTitle>already classified</FieldTitle>
            <FieldTitle>host redshift</FieldTitle>
            <FieldTitle>current mag</FieldTitle>
            <FieldTitle>current age</FieldTitle>
            <FieldTitle>forced photometry requested</FieldTitle>
            <FieldTitle>Assigned for photometry follow-up</FieldTitle>
            <FieldTitle>photometry assigned to</FieldTitle>
            <FieldTitle>Sure if real</FieldTitle>
            <FieldTitle>spectroscopy requested</FieldTitle>
            <FieldTitle>spectroscopy assigned to</FieldTitle>
            <FieldTitle>priority</FieldTitle>
          </Item>
          {candidatesScan.length > 0 ? (
            candidatesScan.map((candidateScan) => (
              <Item
                key={candidateScan.id}
                sx={{ borderBottom: "1px solid #d3d3d3" }}
              >
                <Field>{displayDate(candidateScan.date)}</Field>
                <Field>{candidateScan.scanner}</Field>
                <Field sx={{ flex: 2 }}>{candidateScan.obj_id}</Field>
                <Field sx={{ flex: 3 }}>{candidateScan.comment}</Field>
                <Field>{boolToStr(candidateScan.already_classified)}</Field>
                <Field>{candidateScan.host_redshift}</Field>
                <Field>{candidateScan.current_mag}</Field>
                <Field>{candidateScan.current_age}</Field>
                <Field>
                  {boolToStr(candidateScan.forced_photometry_requested)}
                </Field>
                <Field>{boolToStr(candidateScan.photometry_followup)}</Field>
                <Field>{candidateScan.photometry_assigned_to}</Field>
                <Field>{boolToStr(candidateScan.is_real)}</Field>
                <Field>{boolToStr(candidateScan.spectroscopy_requested)}</Field>
                <Field>{candidateScan.spectroscopy_assigned_to}</Field>
                <Field>{candidateScan.priority}</Field>
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
      photometry_followup: PropTypes.bool,
      photometry_assigned_to: PropTypes.string,
      is_real: PropTypes.bool,
      spectroscopy_requested: PropTypes.bool,
      spectroscopy_assigned_to: PropTypes.string,
      priority: PropTypes.number,
    }),
  ),
};

export default CandidateScanReport;
