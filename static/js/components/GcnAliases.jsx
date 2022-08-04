import React from "react";
import { useSelector, useDispatch } from "react-redux";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";

import * as gcnEventActions from "../ducks/gcnEvent";

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
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  let aliases = [];
  if (gcnEvent.aliases?.length > 0) {
    gcnEvent.aliases?.forEach((alias) => {
      aliases.push(alias);
    });
    aliases = [...new Set(aliases)];
  }

  const handleClick = () => {
    dispatch(gcnEventActions.postGcnAliases(gcnEvent.dateobs)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification("Aliases updated successfully"));
        } else {
          dispatch(showNotification("Error updating aliases", "error"));
        }
      }
    );
  };

  return (
    <div className={classes.root}>
      <h3 className={classes.title}>Aliases: </h3>
      <div className={classes.chips} name="aliases-chips">
        {aliases.map((alias) => (
          <Chip
            size="small"
            label={alias}
            key={alias}
            clickable
            onClick={() => {
              window.open(
                `https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?event=${alias}`,
                "_blank"
              );
            }}
          />
        ))}
        {permission && (
          <Chip
            className={classes.addIcon}
            size="small"
            label="+"
            key="add-aliases"
            name="add-aliases"
            clickable
            onClick={() => {
              handleClick();
            }}
          />
        )}
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
