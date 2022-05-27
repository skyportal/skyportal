import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Button from "@material-ui/core/Button";

const ClassificationShortcutButtons = ({
  selectedClassifications,
  setSelectedClassifications,
  inDialog = false,
}) => {
  const { classificationShortcuts } = useSelector(
    (state) => state.profile.preferences
  );
  const handleClassificationShortcutClick = (shortcutClassifications) => {
    setSelectedClassifications([
      ...new Set([...selectedClassifications, ...shortcutClassifications]),
    ]);
  };
  return (
    <>
      {classificationShortcuts &&
        Object.entries(classificationShortcuts)?.map(
          ([shortcutName, shortcutClassifications]) => (
            <Button
              variant="outlined"
              key={shortcutName}
              data-testid={inDialog ? `${shortcutName}_inDialog` : shortcutName}
              onClick={() =>
                handleClassificationShortcutClick(shortcutClassifications)
              }
            >
              Select {shortcutName}
            </Button>
          )
        )}
    </>
  );
};

ClassificationShortcutButtons.propTypes = {
  selectedClassifications: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedClassifications: PropTypes.func.isRequired,
  inDialog: PropTypes.bool.isRequired,
};

export default ClassificationShortcutButtons;
