import React, { useState } from "react";
import { useDispatch } from "react-redux";
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
  },
  nested: {
    paddingLeft: theme.spacing(4),
    paddingTop: 0,
    paddingBottom: 0,
  },
}));

const CandidateAnnotationsList = ({ annotations }) => {
  const classes = useStyles();

  const dispatch = useDispatch();

  const initState = {};
  annotations.forEach((annotation) => {
    initState[annotation.origin] = true;
  });
  const [openedOrigins, setopenedOrigins] = useState(initState);

  const [selectedKey, setSelectedKey] = useState(null);

  const handleClick = (origin) => {
    setopenedOrigins({ ...openedOrigins, [origin]: !openedOrigins[origin] });
  };

  const handleItemSelect = (keyId, value) => {
    const currentlySelected = selectedKey === keyId;
    setSelectedKey(currentlySelected ? null : keyId);
    /* eslint-disable one-var, prefer-const */
    // ESLint disabled here as it doesn't seem to understand the array destructuring assignment
    let origin, key;
    [, origin, key] = keyId.split("_");
    /* eslint-disable one-var, prefer-const */
    const annotationItem = currentlySelected ? null : { origin, key, value };
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
                let valueString;
                // Only allow sorting by numbers and bools
                let disabled = true;
                const valueType = typeof value;
                switch (valueType) {
                  case "number":
                    valueString = value.toFixed(6);
                    disabled = false;
                    break;
                  case "string":
                    valueString = value.substring(0, 15);
                    break;
                  case "bool":
                    valueString = value.toString();
                    disabled = false;
                    break;
                  default:
                    valueString = value.toString();
                }
                return (
                  <ListItem
                    key={`key_${annotation.origin}_${key}`}
                    button
                    className={classes.nested}
                    selected={selectedKey === `key_${annotation.origin}_${key}`}
                    onClick={() =>
                      handleItemSelect(
                        `key_${annotation.origin}_${key}`,
                        valueString
                      )
                    }
                    disabled={disabled}
                  >
                    <ListItemText secondary={`${key}: ${valueString}`} />
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
