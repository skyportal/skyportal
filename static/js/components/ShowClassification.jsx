import React from "react";
import PropTypes from "prop-types";
import Tooltip from "@material-ui/core/Tooltip";
import Chip from "@material-ui/core/Chip";

import { makeStyles } from "@material-ui/core/styles";

// Export to allow Candidate.jsx to use styles
export const useSourceStyles = makeStyles((theme) => ({
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

function ShowClassification({ classifications, taxonomyList }) {
  const classes = useSourceStyles();

  // Here we compute the most recent non-zero probability class for each taxonomy
  const filteredClasses = classifications.filter((i) => i.probability > 0);
  const groupedClasses = groupBy(filteredClasses, "taxonomy_id");
  const sortedClasses = [];

  Object.keys(groupedClasses).forEach((item) =>
    sortedClasses.push(
      groupedClasses[item].sort((a, b) => (a.modified < b.modified ? 1 : -1))
    )
  );

  if (sortedClasses.length > 0) {
    return (
      <div>
        <b>Classification: </b>
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
};

export default ShowClassification;
