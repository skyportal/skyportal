import React from "react";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";

import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles((theme) => ({
  root: {
    margin: "0",
    padding: "0",
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  circularBody: {
    display: "flex",
    overflow: "auto",
    flexDirection: "column",
  },
}));

const GcnCirculars = ({ gcnEvent }) => {
  const classes = useStyles();
  const styles = useStyles();

  let circulars = [];
  if (gcnEvent.circulars?.length > 0) {
    gcnEvent.circulars?.forEach((circular) => {
      circulars.push(circular);
    });
    circulars = [...new Set(circulars)];
  }

  return (
    <div className={classes.root}>
      {circulars.map((circular) => (
        <Accordion key={circular}>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="circular-content"
            id="circular-header"
          >
            <Typography className={styles.accordionHeading}>
              {circular[0]} - {circular[1]}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.circularBody}>
              <pre>{circular[2]}</pre>
            </div>
          </AccordionDetails>
        </Accordion>
      ))}
    </div>
  );
};

GcnCirculars.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    circulars: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default GcnCirculars;
