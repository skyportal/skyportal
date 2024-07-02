import React from "react";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";

import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
  },
  header: {
    fontSize: "1rem",
  },
}));

const GcnCirculars = ({ gcnEvent }) => {
  const classes = useStyles();
  const styles = useStyles();

  return (
    <div className={classes.root}>
      {gcnEvent.circulars && Object.keys(gcnEvent.circulars)?.length > 0 ? (
        <List>
          {gcnEvent?.circulars &&
            Object.keys(gcnEvent.circulars).map((id) => (
              <>
                <Divider component="li" />
                <ListItem key={id}>
                  <a
                    href={`https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?circular=${id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {gcnEvent.circulars[id]}
                  </a>
                </ListItem>
              </>
            ))}
        </List>
      ) : (
        <Typography className={styles.header}>
          No circulars available for this event yet
        </Typography>
      )}
    </div>
  );
};

GcnCirculars.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    circulars: PropTypes.objectOf(PropTypes.string),
  }).isRequired,
};

export default GcnCirculars;
