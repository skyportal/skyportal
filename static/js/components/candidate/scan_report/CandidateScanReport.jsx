import React from "react";
import PropTypes from "prop-types";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
});

const CandidateScanReport = () => {
  const [scanList, setScanList] = React.useState([]);

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
          {scanList.length > 0 ? (
            scanList.map((scan) => (
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
              <Box sx={{ color: "text.secondary" }}>No scan data</Box>
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
