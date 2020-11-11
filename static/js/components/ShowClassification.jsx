import React from "react";
import PropTypes from "prop-types";
import Tooltip from "@material-ui/core/Tooltip";
import Chip from "@material-ui/core/Chip";

import { makeStyles } from "@material-ui/core/styles";

export const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
}));

const groupBy = (array, key) =>
  array.reduce((result, cv) => {
    // if we've seen this key before, add the value, else generate
    // a new list for this key
    (result[cv[key]] = result[cv[key]] || []).push(cv);
    return result;
  }, {});

export const getSortedClasses = (classifications) => {
  // Here we compute the most recent non-zero probability class for each taxonomy
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const groupedClasses = groupBy(filteredClasses, "taxonomy_id");
  const sortedClasses = [];

  Object.keys(groupedClasses).forEach((item) =>
    sortedClasses.push(
      groupedClasses[item].sort((a, b) => (a.modified < b.modified ? 1 : -1))
    )
  );

  return sortedClasses;
};

export const getLatestClassName = (classifications) => {
  const classes = getSortedClasses(classifications);
  if (classes && classes[0]) return classes[0][0].classification; // TODO: think of a better way to choose from multiple taxonomies
  return "";
};

function ShowClassification({ classifications, taxonomyList, shortened }) {
  const classes = useStyles();

  const sortedClasses = getSortedClasses(classifications);

  const title = shortened ? "" : <b>Classification: </b>;

  if (sortedClasses.length > 0) {
    return (
      <div>
        {title}
        {sortedClasses.map((c) => {
          let name = taxonomyList.filter((i) => i.id === c[0].taxonomy_id);
          if (name.length > 0) {
            name = name[0].name;
          }
          // generate the tooltip for this classification, with an informative
          // hover over.
          return (
            <Tooltip
              key={`${c[0].modified}tt`}
              disableFocusListener
              disableTouchListener
              title={
                <>
                  P=
                  {c[0].probability} ({name}
                  )
                  <br />
                  <i>{c[0].author_name}</i>
                </>
              }
            >
              <Chip
                label={c[0].classification}
                key={`${c[0].modified}tb`}
                size="small"
                className={classes.chip}
              />
            </Tooltip>
          );
        })}
      </div>
    );
  }
  return <span />;
}

ShowClassification.propTypes = {
  classifications: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  taxonomyList: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  shortened: PropTypes.bool,
};
ShowClassification.defaultProps = {
  shortened: false,
};

export default ShowClassification;
