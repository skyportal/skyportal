import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Chip from "@mui/material/Chip";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import CircularProgress from "@mui/material/CircularProgress";
import SaveIcon from "@mui/icons-material/Save";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import * as objectTagsActions from "../../ducks/objectTags";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
  tagDelete: {
    height: "2.1875rem",
    paddingTop: "0.5em",
    paddingBottom: "0.5em",
    alignItems: "center",
  },
}));

const ObjectTags = ({ source }) => {
  const styles = useStyles();
  const dispatch = useDispatch();
  
  // const tagOptions = useSelector((state) => state.objectTags || []);
  const deleteTag = (association_id) => {
    dispatch(objectTagsActions.deleteObjectTag(association_id)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Source Tag deleted"));
        }
      },
    );
  };
  
  return (
    <div className={styles.root}>
      <div className={styles.chips}>
        {source.tags.map((tag) => (
          <Chip
            className={styles.chip}
            key={tag}
            label={tag.text}
            size="small"
            onDelete={() => deleteTag(tag.id)}
          />
        ))}
      
      </div>
    </div>
  );
};

ObjectTags.propTypes = {
  source: PropTypes.shape({
    tags: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number,
      text: PropTypes.string
    })),
  }).isRequired,
};

export default ObjectTags;