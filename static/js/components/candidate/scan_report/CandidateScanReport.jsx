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

  return (
    <Box sx={{ container: "true", padding: 2 }}>
      <Typography variant="h5" sx={{ marginBottom: "0.5rem" }}>
        <b>Candidate scan report</b>
      </Typography>
      <Paper sx={{ padding: "2rem" }}>
        <List>
          <Item
            sx={{
              fontWeight: "bold",
              paddingBottom: "0.5rem",
              marginBottom: "0.5rem",
              borderBottom: "1px solid grey",
            }}
          >
            <Box sx={{ flex: 1 }}>date</Box>
            <Box sx={{ flex: 1 }}>name</Box>
            <Box sx={{ flex: 1 }}>ztf_name</Box>
            <Box sx={{ flex: 2 }}>comment</Box>
          </Item>
          {candidatesScan.length > 0 ? (
            candidatesScan.map((scan) => (
              <Item key={scan.id}>
                <Box sx={{ flex: 1 }}>{scan.date}</Box>
                <Box sx={{ flex: 1 }}>{scan.name}</Box>
                <Box sx={{ flex: 1 }}>{scan.ztf_name}</Box>
                <Box sx={{ flex: 2 }}>{scan.comment}</Box>
              </Item>
            ))
          ) : (
            <Item
              sx={{
                display: "flex",
                justifyContent: "center",
                paddingY: "1rem",
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
      name: PropTypes.string.isRequired,
      ztf_name: PropTypes.string.isRequired,
      comment: PropTypes.string.isRequired,
    }),
  ),
};

export default CandidateScanReport;
