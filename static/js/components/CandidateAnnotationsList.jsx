import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { makeStyles } from "@material-ui/core/styles";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Collapse from "@material-ui/core/Collapse";
import ExpandLess from "@material-ui/icons/ExpandLess";
import ExpandMore from "@material-ui/icons/ExpandMore";
import Divider from "@material-ui/core/Divider";

import * as candidatesActions from "../ducks/candidates";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    background: theme.palette.background.paper,
    padding: theme.spacing(1),
    maxHeight: "15rem",
    overflowY: "scroll",
    // Prevent disabled annotations from being selected, but display normally for readability
    "& .Mui-disabled": {
      opacity: 1,
    },
  },
  nested: {
    paddingLeft: theme.spacing(4),
    paddingTop: 0,
    paddingBottom: 0,
  },
}));

export const getAnnotationValueString = (value) => {
  let valueString;
  const valueType = typeof value;
  switch (valueType) {
    case "number":
      valueString = value.toFixed(6);
      break;
    case "string":
      valueString = `${value.substring(0, 15)}...`;
      break;
    default:
      valueString = value.toString();
  }
  return valueString;
};

const CandidateAnnotationsList = ({ annotations }) => {
  const classes = useStyles();

  const dispatch = useDispatch();

  const initState = {};
  annotations.forEach((annotation) => {
    initState[annotation.origin] = true;
  });
  const [openedOrigins, setopenedOrigins] = useState(initState);

  const selectedAnnotationItem = useSelector(
    (state) => state.candidates.selectedAnnotationItem
  );

  const handleClick = (origin) => {
    setopenedOrigins({ ...openedOrigins, [origin]: !openedOrigins[origin] });
  };

  const handleItemSelect = (origin, key) => {
    const currentlySelected =
      selectedAnnotationItem &&
      selectedAnnotationItem.origin === origin &&
      selectedAnnotationItem.key === key;

    const annotationItem = currentlySelected ? null : { origin, key };
    dispatch(candidatesActions.setCandidatesAnnotationItem(annotationItem));
  };

  return (
    <List
      component="nav"
      aria-labelledby="nested-list-subheader"
      className={classes.root}
      dense
    >
      {annotations.map((annotation) => (
        <div key={`annotation_${annotation.origin}`}>
          <Divider />
          <ListItem button onClick={() => handleClick(annotation.origin)}>
            <ListItemText
              primary={`${annotation.origin}`}
              primaryTypographyProps={{ variant: "button" }}
            />
            {openedOrigins[annotation.origin] ? <ExpandLess /> : <ExpandMore />}
          </ListItem>
          <Collapse
            in={openedOrigins[annotation.origin]}
            timeout="auto"
            unmountOnExit
          >
            <List component="div" dense disablePadding>
              {Object.entries(annotation.data).map(([key, value]) => {
                // Only allow sorting by numbers and bools
                let disabled;
                switch (typeof value) {
                  case "number":
                  case "boolean":
                    disabled = false;
                    break;
                  default:
                    disabled = true;
                }
                return (
                  <ListItem
                    key={`key_${annotation.origin}_${key}`}
                    button
                    className={classes.nested}
                    selected={
                      selectedAnnotationItem &&
                      selectedAnnotationItem.origin === annotation.origin &&
                      selectedAnnotationItem.key === key
                    }
                    onClick={() => handleItemSelect(annotation.origin, key)}
                    disabled={disabled}
                  >
                    <ListItemText
                      secondary={`${key}: ${getAnnotationValueString(value)}`}
                    />
                  </ListItem>
                );
              })}
            </List>
          </Collapse>
          <Divider />
        </div>
      ))}
    </List>
  );
};

CandidateAnnotationsList.propTypes = {
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      origin: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    })
  ).isRequired,
};

export default CandidateAnnotationsList;
