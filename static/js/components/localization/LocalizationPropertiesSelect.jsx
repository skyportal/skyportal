import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";
import SelectWithChips from "../SelectWithChips";

import * as localizationPropertiesActions from "../../ducks/localizationProperties";

const useStyles = makeStyles(() => ({
  root: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
  form_group: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "justify-between",
    alignItems: "top",
    gap: "0.2rem",
    width: "100%",
  },
  formItem: {
    width: "100%",
  },
  select: {
    width: "100%",
    height: "3rem",
    "& > div": {
      width: "100%",
      height: "3rem",
    },
  },
  selectWithMargin: {
    width: "100%",
    height: "3rem",
    "& > div": {
      width: "100%",
      height: "3rem",
    },
    marginBottom: "0.5rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

const LocalizationPropertiesSelect = (props) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { selectedLocalizationProperties, setSelectedLocalizationProperties } =
    props;

  let localizationProperties = [];
  localizationProperties = localizationProperties.concat(
    useSelector((state) => state.localizationProperties),
  );
  localizationProperties.sort();

  const comparators = {
    lt: "<",
    le: "<=",
    eq: "=",
    ne: "!=",
    ge: ">",
    gt: ">=",
  };

  useEffect(() => {
    dispatch(localizationPropertiesActions.fetchLocalizationProperties());
  }, [dispatch]);

  const handleChange = (event) =>
    setSelectedLocalizationProperties(event.target.value);

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleSubmitProperties = async () => {
    const filterData = getValues();
    const propertiesFilter = `${filterData.property}: ${filterData.propertyComparatorValue}: ${filterData.propertyComparator}`;
    const selectedLocalizationPropertiesCopy = [
      ...selectedLocalizationProperties,
    ];
    selectedLocalizationPropertiesCopy.push(propertiesFilter);
    setSelectedLocalizationProperties(selectedLocalizationPropertiesCopy);
  };

  const handleClickReset = () => {
    reset();
  };

  return (
    <div>
      <form className={classes.root}>
        <div className={classes.form_group}>
          <div className={classes.formItem}>
            <Controller
              render={({ field: { value } }) => (
                <>
                  <InputLabel>Property</InputLabel>
                  <Select
                    inputProps={{ MenuProps: { disableScrollLock: true } }}
                    labelId="localizationPropertySelectLabel"
                    value={value || ""}
                    onChange={(event) => {
                      reset({
                        ...getValues(),
                        property:
                          event.target.value === -1 ? "" : event.target.value,
                      });
                    }}
                    className={classes.select}
                  >
                    {localizationProperties?.map((localizationProperty) => (
                      <MenuItem
                        value={localizationProperty}
                        key={localizationProperty}
                        className={classes.selectItem}
                      >
                        {`${localizationProperty}`}
                      </MenuItem>
                    ))}
                  </Select>
                </>
              )}
              name="property"
              control={control}
              defaultValue=""
            />
          </div>
          <div className={classes.formItem}>
            <Controller
              render={({ field: { value } }) => (
                <>
                  <InputLabel>Comparator</InputLabel>
                  <Select
                    inputProps={{ MenuProps: { disableScrollLock: true } }}
                    labelId="localizationPropertyComparatorSelectLabel"
                    value={value || ""}
                    onChange={(event) => {
                      reset({
                        ...getValues(),
                        propertyComparator:
                          event.target.value === -1 ? "" : event.target.value,
                      });
                    }}
                    className={classes.select}
                  >
                    {Object.keys(comparators)?.map((key) => (
                      <MenuItem
                        value={key}
                        key={key}
                        className={classes.selectItem}
                      >
                        {`${comparators[key]}`}
                      </MenuItem>
                    ))}
                  </Select>
                </>
              )}
              name="propertyComparator"
              control={control}
              defaultValue="="
            />
          </div>
          <div className={classes.formItem}>
            <Controller
              render={({ field: { onChange, value } }) => (
                <>
                  <InputLabel>Value</InputLabel>
                  <TextField
                    size="small"
                    name="propertyComparatorValue"
                    inputRef={register("propertyComparatorValue")}
                    placeholder="0.0"
                    onChange={onChange}
                    value={value}
                    className={classes.select}
                  />
                </>
              )}
              name="propertyComparatorValue"
              control={control}
            />
          </div>
        </div>
        <div className={classes.form_group}>
          <ButtonGroup
            variant="contained"
            color="primary"
            aria-label="contained primary button group"
          >
            <Button primary onClick={handleSubmit(handleSubmitProperties)}>
              Add
            </Button>
            <Button primary onClick={handleClickReset}>
              Reset
            </Button>
          </ButtonGroup>
        </div>
      </form>
      <div className={classes.selectWithMargin}>
        <SelectWithChips
          label="Localization Properties"
          id="selectLocalizations"
          initValue={selectedLocalizationProperties}
          onChange={handleChange}
          options={selectedLocalizationProperties}
        />
      </div>
    </div>
  );
};

LocalizationPropertiesSelect.propTypes = {
  selectedLocalizationProperties: PropTypes.arrayOf(PropTypes.string)
    .isRequired,
  setSelectedLocalizationProperties: PropTypes.func.isRequired,
};

export default LocalizationPropertiesSelect;
