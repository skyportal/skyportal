import React from "react";
import { useDispatch } from "react-redux";
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

const comparators = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

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

const PlanPropertiesSelect = (props) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { selectedPlanProperties, setSelectedPlanProperties } = props;

  let planProperties = [
    "area",
    "num_observations",
    "probability",
    "tot_time_with_overhead",
    "total_time",
  ];

  const handleChange = (event) => {
    setSelectedPlanProperties(event.target.value);
  };

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleSubmitProperties = async () => {
    const filterData = getValues();
    const propertiesFilter = `${filterData.property}: ${filterData.propertyComparatorValue}: ${filterData.propertyComparator}`;
    const selectedPlanPropertiesCopy = [...selectedPlanProperties];
    selectedPlanPropertiesCopy.push(propertiesFilter);
    setSelectedPlanProperties(selectedPlanPropertiesCopy);
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
                    labelId="PlanPropertySelectLabel"
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
                    {planProperties?.map((planProperty) => (
                      <MenuItem
                        value={planProperty}
                        key={planProperty}
                        className={classes.selectItem}
                      >
                        {`${planProperty}`}
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
                    labelId="planPropertyComparatorSelectLabel"
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
          label="Plan Properties"
          id="selectPlanProperties"
          initValue={selectedPlanProperties}
          onChange={handleChange}
          options={selectedPlanProperties}
        />
      </div>
    </div>
  );
};

PlanPropertiesSelect.propTypes = {
  selectedPlanProperties: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedPlanProperties: PropTypes.func.isRequired,
};

export default PlanPropertiesSelect;
