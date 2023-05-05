import React from "react";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
  },
  title: {
    margin: "0",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: "0",
      margin: "0.25rem",
    },
  },
  addIcon: {
    fontSize: "1rem",
  },
}));

const GcnAliases = ({ gcnEvent }) => {
  const classes = useStyles();

  let aliases = [];
  if (gcnEvent.aliases?.length > 0) {
    gcnEvent.aliases?.forEach((alias) => {
      aliases.push(alias);
    });
    aliases = [...new Set(aliases)];
  }

  return (
    <div className={classes.root}>
      <div className={classes.chips} name="aliases-chips">
        {aliases.map((alias) => (
          <Chip
            size="small"
            label={alias}
            key={alias}
            clickable
            onClick={() => {
              window.open(
                `https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?event=${
                  alias.split("#")[1] || alias
                }`,
                "_blank"
              );
            }}
          />
        ))}
      </div>
    </div>
  );
};

GcnAliases.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    aliases: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default GcnAliases;
