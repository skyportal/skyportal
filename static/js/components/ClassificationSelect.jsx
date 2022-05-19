import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import Chip from "@material-ui/core/Chip";
import FormControl from "@material-ui/core/FormControl";
import { makeStyles, useTheme } from "@material-ui/core/styles";
import { allowedClasses } from "./ClassificationForm";
import ClassificationShortcutButtons from "./ClassificationShortcutButtons";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "20rem",
  },
  classificationsMenu: {
    minWidth: "12rem",
  },
  shortcutButtons: {
    margin: "1rem 0",
  },
}));

const getStyles = (classification, selectedClassifications, theme) => ({
  fontWeight:
    selectedClassifications.indexOf(classification) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

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
      (option) => option.class
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();
  const classes = useStyles();
  const theme = useTheme();

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

  return (
    <>
      <div>
        <FormControl className={classes.classificationsMenu}>
          <InputLabel id="classifications-select-label">
            Classifications
          </InputLabel>
          <Select
            labelId="classifications-select-label"
            id="classifications-select"
            multiple
            value={selectedClassifications}
            onChange={(event) => {
              setSelectedClassifications(event.target.value);
            }}
            input={<Input id="classifications-select" />}
            renderValue={(selected) => (
              <div className={classes.chips}>
                {selected?.map((classification) => (
                  <Chip key={classification} label={classification} />
                ))}
              </div>
            )}
            MenuProps={MenuProps}
          >
            {classifications?.map((classification) => (
              <MenuItem
                key={classification}
                value={classification}
                style={getStyles(
                  classification,
                  selectedClassifications,
                  theme
                )}
              >
                {classification}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
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
