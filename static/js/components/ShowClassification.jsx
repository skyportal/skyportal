import React from "react";
import PropTypes from "prop-types";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";

import makeStyles from "@mui/styles/makeStyles";

export const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
    fontSize: "1.2rem",
    fontWeight: "bold",
  },
}));

const ClassificationRow = ({ classifications }) => {
  const classes = useStyles();

  const classification = classifications[0];
  return (
    <div>
      <Tooltip
        key={`${classification.modified}tt`}
        disableFocusListener
        disableTouchListener
        title={
          <div>
            {classifications.map((cls) => (
              <>
                P=
                {cls.probability} ({cls.taxname})
                <br />
                <i>{cls.author_name}</i>
                <br />
              </>
            ))}
          </div>
        }
      >
        <Chip
          label={
            classification.probability < 0.1
              ? `${classification.classification}?`
              : classification.classification
          }
          key={`${classification.modified}tb`}
          size="small"
          className={classes.chip}
        />
      </Tooltip>
    </div>
  );
};

ClassificationRow.propTypes = {
  classifications: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      classification: PropTypes.string,
      created_at: PropTypes.string,
      author_name: PropTypes.string,
      modified: PropTypes.string,
      probability: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
};

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
  const sorted_classifications = classifications.sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );

  const classificationsGrouped = sorted_classifications.reduce((r, a) => {
    r[a.classification] = [...(r[a.classification] || []), a];
    return r;
  }, {});

  const keys = Object.keys(classificationsGrouped);
  keys.forEach((key) => {
    classificationsGrouped[key].forEach((item, index) => {
      let taxname = taxonomyList.filter(
        (i) => i.id === classificationsGrouped[key][index].taxonomy_id
      );
      if (taxname.length > 0) {
        taxname = taxname[0].name;
      } else {
        taxname = "Unknown taxonomy";
      }
      classificationsGrouped[key][index].taxname = taxname;
    });
  });

  const title = shortened ? "" : <b>Classification: </b>;

  return (
    <div>
      {title}
      {keys.map((key) => (
        <ClassificationRow
          key={key}
          classifications={classificationsGrouped[key]}
        />
      ))}
    </div>
  );
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
