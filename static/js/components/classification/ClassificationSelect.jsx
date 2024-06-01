import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import { allowedClasses } from "./ClassificationForm";
import ClassificationShortcutButtons from "./ClassificationShortcutButtons";
import SelectWithChips from "../SelectWithChips";

const useStyles = makeStyles(() => ({
  shortcutButtons: {
    margin: "1rem 0",
  },
}));

const ClassificationSelect = (props) => {
  const {
    selectedClassifications,
    setSelectedClassifications,
    showShortcuts = false,
    inDialog = false,
  } = props;

  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();
  const classes = useStyles();

  const onClassificationSelectChange = (event) => {
    setSelectedClassifications(event.target.value);
  };

  return (
    <>
      <div>
        <SelectWithChips
          label="Classifications"
          id="classifications-select"
          initValue={selectedClassifications}
          onChange={onClassificationSelectChange}
          options={classifications}
        />
      </div>
      <div className={classes.shortcutButtons}>
        {showShortcuts && (
          <ClassificationShortcutButtons
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
            inDialog={inDialog}
          />
        )}
      </div>
    </>
  );
};

ClassificationSelect.propTypes = {
  selectedClassifications: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedClassifications: PropTypes.func.isRequired,
  showShortcuts: PropTypes.bool,
  inDialog: PropTypes.bool,
};

ClassificationSelect.defaultProps = {
  showShortcuts: false,
  inDialog: false,
};

export default ClassificationSelect;
