import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import CandidateThumbnails from "./CandidateThumbnails";
import CandidateInfo from "./CandidateInfo";
import CandidatePhotometry from "./CandidatePhotometry";
import CandidateAutoannotations from "./CandidateAutoannotations";

const useStyles = makeStyles((theme) => ({
  listPaper: {
    borderColor: theme.palette.grey[350],
    borderWidth: "2px",
    marginBottom: "1rem",
  },
  candidatePaper: {
    display: "grid",
    padding: "0.5rem",
    alignItems: "center",
    gridColumnGap: 0,
    gridRowGap: "0.5rem",
    justifyContent: "space-between",
    // we change the order of the children and the layout based on the screen size
    [theme.breakpoints.up("lg")]: {
      gridTemplateColumns: "32% 16% 32% 20%",
      gridTemplateAreas: `"thumbnails info photometry annotations"`,
    },
    [theme.breakpoints.down("lg")]: {
      gridTemplateAreas: `"thumbnails info" "photometry annotations"`,
      gridTemplateColumns: "60% 40%",
    },
    [theme.breakpoints.down("sm")]: {
      gridTemplateAreas: `"info" "thumbnails" "photometry" "annotations"`,
      gridTemplateColumns: "100%",
    },
  },
}));

/**
 * Card displayed in the scanning search results of the CandidateList
 */
const Candidate = ({ candidate, filterGroups, index, totalMatches }) => {
  const classes = useStyles();
  return (
    <Paper
      variant="outlined"
      className={classes.listPaper}
      data-testid={`candidate-${index}`}
    >
      <div className={classes.candidatePaper}>
        <div style={{ gridArea: "thumbnails" }}>
          <CandidateThumbnails
            id={candidate.id}
            ra={candidate.ra}
            dec={candidate.dec}
            thumbnails={candidate.thumbnails}
          />
        </div>
        <div style={{ gridArea: "info", padding: "0 0 0 0.25rem" }}>
          <CandidateInfo candidateObj={candidate} filterGroups={filterGroups} />
        </div>
        <div style={{ gridArea: "photometry" }}>
          <CandidatePhotometry sourceId={candidate.id} />
        </div>
        <div
          style={{
            gridArea: "annotations",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            minHeight: "100%",
            paddingLeft: "1rem",
          }}
        >
          <CandidateAutoannotations
            annotations={candidate.annotations}
            filterGroups={filterGroups}
          />
          {/* here show a counter, saying this is candidate n/m */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              paddingTop: "0.5rem",
            }}
          >
            <Typography fontWeight="bold">
              {`${index}/${totalMatches}`}
            </Typography>
          </div>
        </div>
      </div>
    </Paper>
  );
};

Candidate.displayName = "Candidate";

Candidate.propTypes = {
  candidate: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number.isRequired,
    dec: PropTypes.number.isRequired,
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    annotations: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})),
  index: PropTypes.number.isRequired,
  totalMatches: PropTypes.number.isRequired,
};

Candidate.defaultProps = {
  filterGroups: [],
};

export default Candidate;
