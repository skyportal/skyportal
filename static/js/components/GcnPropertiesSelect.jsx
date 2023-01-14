import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { useForm, Controller } from "react-hook-form";
import Button from "./Button";
import SelectWithChips from "./SelectWithChips";

import * as gcnPropertiesActions from "../ducks/gcnProperties";

const useStyles = makeStyles((theme) => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  paper: {
    padding: "1rem",
    marginTop: "1rem",
    maxHeight: "calc(100vh - 5rem)",
    overflow: "scroll",
  },
  root: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "space-between",
    "& .MuiTextField-root": {
      margin: theme.spacing(0.2),
      width: "10rem",
    },
  },
  formItem: {
    flex: "1 1 45%",
    margin: "0.5rem",
  },
  formItemRightColumn: {
    flex: "1 1 90%",
    margin: "0.5rem",
  },
  positionField: {
    width: "33%",
    "& > label": {
      fontSize: "0.875rem",
      [theme.breakpoints.up("sm")]: {
        fontSize: "1rem",
      },
    },
  },
  formButtons: {
    width: "100%",
    margin: "0.5rem",
  },
  title: {
    margin: "0.5rem 0rem 0rem 0rem",
  },
  multiSelect: {
    maxWidth: "100%",
    "& > div": {
      whiteSpace: "normal",
    },
  },
  checkboxGroup: {
    display: "flex",
    flexWrap: "wrap",
    width: "100%",
    "& > label": {
      marginRight: "1rem",
    },
  },
  select: {
    width: "40%",
    height: "3rem",
  },
  selectItems: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "left",
    gap: "0.25rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

const GcnPropertiesSelect = (props) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { selectedGcnProperties, setSelectedGcnProperties } = props;

  let gcnProperties = [];
  gcnProperties = gcnProperties.concat(
    useSelector((state) => state.gcnProperties)
  );
  gcnProperties.sort();

  const comparators = {
    lt: "<",
    le: "<=",
    eq: "=",
    ne: "!=",
    ge: ">",
    gt: ">=",
  };

  useEffect(() => {
    dispatch(gcnPropertiesActions.fetchGcnProperties());
  }, [dispatch]);

  const handleChange = (event) => setSelectedGcnProperties(event.target.value);

  const { handleSubmit, register, control, reset, getValues } = useForm();

  const handleSubmitProperties = async () => {
    const filterData = getValues();
    const propertiesFilter = `${filterData.property}: ${filterData.propertyComparatorValue}: ${filterData.propertyComparator}`;
    const selectedGcnPropertiesCopy = [...selectedGcnProperties];
    selectedGcnPropertiesCopy.push(propertiesFilter);
    setSelectedGcnProperties(selectedGcnPropertiesCopy);
  };

  const handleClickReset = () => {
    reset();
  };

  return (
    <div>
      <div>
        <form className={classes.root}>
          <div className={classes.formItemRightColumn}>
            <Typography variant="subtitle2" className={classes.title}>
              GCN Property Filtering
            </Typography>
            <div className={classes.selectItems}>
              <Controller
                render={({ field: { value } }) => (
                  <Select
                    inputProps={{ MenuProps: { disableScrollLock: true } }}
                    labelId="gcnPropertySelectLabel"
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
                    {gcnProperties?.map((gcnProperty) => (
                      <MenuItem
                        value={gcnProperty}
                        key={gcnProperty}
                        className={classes.selectItem}
                      >
                        {`${gcnProperty}`}
                      </MenuItem>
                    ))}
                  </Select>
                )}
                name="property"
                control={control}
                defaultValue=""
              />
            </div>
            <div className={classes.selectItems}>
              <Controller
                render={({ field: { value } }) => (
                  <Select
                    inputProps={{ MenuProps: { disableScrollLock: true } }}
                    labelId="gcnPropertyComparatorSelectLabel"
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
                )}
                name="propertyComparator"
                control={control}
                defaultValue="="
              />
            </div>
            <Controller
              render={({ field: { onChange, value } }) => (
                <TextField
                  size="small"
                  label="Property Comparator Value"
                  name="propertyComparatorValue"
                  inputRef={register("propertyComparatorValue")}
                  placeholder="0.0"
                  onChange={onChange}
                  value={value}
                />
              )}
              name="propertyComparatorValue"
              control={control}
            />
          </div>

          <div className={classes.formButtons}>
            <ButtonGroup
              variant="contained"
              color="primary"
              aria-label="contained primary button group"
            >
              <Button primary onClick={handleSubmit(handleSubmitProperties)}>
                Submit
              </Button>
              <Button primary onClick={handleClickReset}>
                Reset
              </Button>
            </ButtonGroup>
          </div>
        </form>
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <SelectWithChips
          label="Gcn Properties"
          id="selectGcns"
          initValue={selectedGcnProperties}
          onChange={handleChange}
          options={selectedGcnProperties}
        />
      </div>
    </div>
  );
};

GcnPropertiesSelect.propTypes = {
  selectedGcnProperties: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedGcnProperties: PropTypes.func.isRequired,
};

export default GcnPropertiesSelect;
