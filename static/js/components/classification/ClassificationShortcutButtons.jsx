import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Button from "../Button";

const ClassificationShortcutButtons = ({
  selectedClassifications,
  setSelectedClassifications,
  inDialog = false,
}) => {
  const { classificationShortcuts } = useSelector(
    (state) => state.profile.preferences,
  );
  if (!classificationShortcuts) return null;

  const handleClassificationShortcutClick = (shortcutClassifications) => {
    setSelectedClassifications([
      ...new Set([...selectedClassifications, ...shortcutClassifications]),
    ]);
  };

  return Object.entries(classificationShortcuts)?.map(
    ([shortcutName, shortcutClassifications]) => (
      <Button
        secondary
        key={shortcutName}
        data-testid={shortcutName + (inDialog ? `_inDialog` : "")}
        onClick={() =>
          handleClassificationShortcutClick(shortcutClassifications)
        }
      >
        Select {shortcutName}
      </Button>
    ),
  );
};

ClassificationShortcutButtons.propTypes = {
  selectedClassifications: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedClassifications: PropTypes.func.isRequired,
  inDialog: PropTypes.bool.isRequired,
};

export default ClassificationShortcutButtons;
