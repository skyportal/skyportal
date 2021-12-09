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

  Object.keys(groupedClasses)?.forEach((item) =>
    sortedClasses.push(
      groupedClasses[item].sort((a, b) => (a.modified < b.modified ? 1 : -1))
    )
  );

  return sortedClasses;
};

function ShowClassification({ classifications, taxonomyList, shortened }) {
  const classes = useStyles();

  const sortedClasses = getSortedClasses(classifications);

  const title = shortened ? "" : <b>Classification: </b>;

  if (sortedClasses.length > 0) {
    return (
      <div>
        {title}
        {sortedClasses.map((classesGroup) => {
          let name = taxonomyList.filter(
            (i) => i.id === classesGroup[0]?.taxonomy_id
          );
          if (name.length > 0) {
            name = name[0].name;
          }
          return classesGroup.map((cls) => (
            // generate the tooltip for this classification, with an informative
            // hover over.
            <Tooltip
              key={`${cls.modified}tt`}
              disableFocusListener
              disableTouchListener
              title={
                <>
                  P=
                  {cls.probability} ({name}
                  )
                  <br />
                  <i>{cls.author_name}</i>
                </>
              }
            >
              <Chip
                label={cls.classification}
                key={`${cls.modified}tb`}
                size="small"
                className={classes.chip}
              />
            </Tooltip>
          ));
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
