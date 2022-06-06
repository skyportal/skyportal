import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import Chip from "@material-ui/core/Chip";
import FormControl from "@material-ui/core/FormControl";
import { makeStyles, useTheme } from "@material-ui/core/styles";

import { fetchGcnNoticeTypes } from "../ducks/gcnNoticeTypes";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "20rem",
  },
  gcnNoticesMenu: {
    minWidth: "12rem",
  },
}));

const getStyles = (gcn_notice_type, selectedGcnNoticeTypes, theme) => ({
  fontWeight:
    selectedGcnNoticeTypes.indexOf(gcn_notice_type) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const GcnNoticeTypesSelect = (props) => {
  const { selectedGcnNoticeTypes, setSelectedGcnNoticeTypes } = props;

  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const gcn_notice_types = useSelector(
    (state) => state.gcnNoticeTypes.gcnNoticeTypes
  );

  console.log("selected gcn notice types: ", selectedGcnNoticeTypes);

  useEffect(() => {
    dispatch(fetchGcnNoticeTypes());
  }, []);

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
      {gcn_notice_types?.length > 0 && (
        <div>
          <FormControl className={classes.gcnNoticesMenu}>
            <InputLabel id="gcn-notice-types-input-label">
              Gcn Notice Types
            </InputLabel>
            <Select
              labelId="gcn-notice-types-select-label"
              id="gcn-notice-types-select"
              multiple
              value={selectedGcnNoticeTypes}
              onChange={(event) => {
                setSelectedGcnNoticeTypes(event.target.value);
              }}
              input={<Input id="gcn-notice-types-select" />}
              renderValue={(selected) => (
                <div className={classes.chips}>
                  {selected?.map((gcn_notice_type) =>
                    selected.indexOf(gcn_notice_type) === 0 ? (
                      <Chip key={gcn_notice_type} label={gcn_notice_type} />
                    ) : (
                      selected.indexOf(gcn_notice_type) === 1 && (
                        <Chip
                          key={gcn_notice_type}
                          label={`+${selected?.length - 1}`}
                        />
                      )
                    )
                  )}
                </div>
              )}
              MenuProps={MenuProps}
            >
              {gcn_notice_types?.map((gcn_notice_type) => (
                <MenuItem
                  key={gcn_notice_type}
                  value={gcn_notice_type}
                  style={getStyles(
                    gcn_notice_type,
                    selectedGcnNoticeTypes,
                    theme
                  )}
                >
                  {gcn_notice_type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </div>
      )}
    </>
  );
};

GcnNoticeTypesSelect.propTypes = {
  selectedGcnNoticeTypes: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnNoticeTypes: PropTypes.func.isRequired,
};

export default GcnNoticeTypesSelect;
