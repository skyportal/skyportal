import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Collapse from "@mui/material/Collapse";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Divider from "@mui/material/Divider";

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
      valueString = value.toFixed(4);
      break;
    case "object":
      valueString = JSON.stringify(value, null, 2);
      break;
    default:
      valueString = value.toString();
  }
  return valueString;
};
const ScanningPageCandidateAnnotations = ({
  annotations,
  listWidth = 250,
  listItemWidth = 200,
}) => {
  const classes = useStyles();

  const dispatch = useDispatch();

  const initState = {};
  annotations?.forEach((annotation) => {
    initState[annotation.origin] = true;
  });
  const [openedOrigins, setOpenedOrigins] = useState(initState);

  const selectedAnnotationSortOptions = useSelector(
    (state) => state.candidates.selectedAnnotationSortOptions
  );

  const handleClick = (origin) => {
    setOpenedOrigins({ ...openedOrigins, [origin]: !openedOrigins[origin] });
  };

  const handleItemSelect = (origin, key) => {
    const currentlySelected =
      selectedAnnotationSortOptions &&
      selectedAnnotationSortOptions.origin === origin &&
      selectedAnnotationSortOptions.key === key;

    const annotationItem = currentlySelected
      ? null
      : { origin, key, order: null };
    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions(annotationItem)
    );
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
            <List
              component="div"
              sx={{ maxWidth: listWidth }}
              dense
              disablePadding
            >
              {Object.entries(annotation.data).map(([key, value]) => (
                <ListItem
                  key={`key_${annotation.origin}_${key}`}
                  button
                  className={classes.nested}
                  selected={
                    selectedAnnotationSortOptions &&
                    selectedAnnotationSortOptions.origin ===
                      annotation.origin &&
                    selectedAnnotationSortOptions.key === key
                  }
                  onClick={() => handleItemSelect(annotation.origin, key)}
                >
                  <ListItemText
                    secondaryTypographyProps={{
                      sx: { maxWidth: listItemWidth },
                    }}
                    secondary={`${key}: ${getAnnotationValueString(value)}`}
                  />
                </ListItem>
              ))}
            </List>
          </Collapse>
          <Divider />
        </div>
      ))}
    </List>
  );
};

ScanningPageCandidateAnnotations.propTypes = {
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      origin: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    })
  ).isRequired,
  listWidth: PropTypes.number,
  listItemWidth: PropTypes.number,
};

ScanningPageCandidateAnnotations.defaultProps = {
  listWidth: 250,
  listItemWidth: 200,
};

export default ScanningPageCandidateAnnotations;
