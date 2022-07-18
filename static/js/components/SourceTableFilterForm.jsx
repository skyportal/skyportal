import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Input from "@mui/material/Input";
import Chip from "@mui/material/Chip";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { useForm, Controller } from "react-hook-form";

import { allowedClasses } from "./ClassificationForm";

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
    flex: "1 1 50%",
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
}));

const getMultiselectStyles = (value, selectedValues, theme) => ({
  fontWeight:
    selectedValues.indexOf(value) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const SourceTableFilterForm = ({ handleFilterSubmit }) => {
  const classes = useStyles();
  const theme = useTheme();

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
      },
    },
  };

  // Get unique classification names, in alphabetical order
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) => `${taxonomy.name}: ${option.class}`
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const [selectedClassifications, setSelectedClassifications] = useState([]);
  const [selectedNonClassifications, setSelectedNonClassifications] = useState(
    []
  );

  const { handleSubmit, register, control, reset } = useForm();

  const handleClickReset = () => {
    reset();
  };

  return (
    <Paper className={classes.paper} variant="outlined">
      <div>
        <h4> Filter Sources By</h4>
      </div>
      <form
        className={classes.root}
        onSubmit={handleSubmit(handleFilterSubmit)}
      >
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Name or ID
          </Typography>
          <TextField
            label="Source ID/Name"
            name="sourceID"
            inputRef={register}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Position
          </Typography>
          <TextField
            size="small"
            label="RA (deg)"
            name="position.ra"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
            className={classes.positionField}
          />
          <TextField
            size="small"
            label="Dec (deg)"
            name="position.dec"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
            className={classes.positionField}
          />
          <TextField
            size="small"
            label="Radius (deg)"
            name="position.radius"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
            className={classes.positionField}
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Time Saved (UTC)
          </Typography>
          <TextField
            size="small"
            label="Saved After"
            name="savedAfter"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
          <TextField
            size="small"
            label="Saved Before"
            name="savedBefore"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Time Last Detected (UTC)
          </Typography>
          <TextField
            size="small"
            label="Last Detected After"
            name="startDate"
            inputRef={register}
            placeholder="2012-08-30T00:00:00"
          />
          <TextField
            size="small"
            label="Last Detected Before"
            name="endDate"
            inputRef={register}
            placeholder="2012-08-30T00:00:00"
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Simbad Class
          </Typography>
          <TextField
            size="small"
            label="Class Name"
            type="text"
            name="simbadClass"
            inputRef={register}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Classification
          </Typography>
          <Controller
            render={({ onChange, value }) => (
              <Select
                labelId="classifications-select-label"
                data-testid="classifications-select"
                multiple
                value={value}
                onChange={(event) => {
                  setSelectedClassifications(event.target.value);
                  onChange(event.target.value);
                }}
                input={
                  <Input
                    className={classes.multiSelect}
                    id="classifications-select"
                  />
                }
                renderValue={(selected) => (
                  <div className={classes.chips}>
                    {selected.map((classification) => (
                      <Chip
                        key={classification}
                        label={classification}
                        className={classes.chip}
                      />
                    ))}
                  </div>
                )}
                MenuProps={MenuProps}
              >
                {classifications.map((classification) => (
                  <MenuItem
                    key={classification}
                    value={classification}
                    style={getMultiselectStyles(
                      classification,
                      selectedClassifications,
                      theme
                    )}
                  >
                    {classification}
                  </MenuItem>
                ))}
              </Select>
            )}
            name="classifications"
            control={control}
            defaultValue={[]}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Non-Classifications
          </Typography>
          <Controller
            render={({ onChange, value }) => (
              <Select
                labelId="classifications-select-label"
                data-testid="classifications-select"
                multiple
                value={value}
                onChange={(event) => {
                  setSelectedNonClassifications(event.target.value);
                  onChange(event.target.value);
                }}
                input={
                  <Input
                    className={classes.multiSelect}
                    id="classifications-select"
                  />
                }
                renderValue={(selected) => (
                  <div className={classes.chips}>
                    {selected.map((classification) => (
                      <Chip
                        key={classification}
                        label={classification}
                        className={classes.chip}
                      />
                    ))}
                  </div>
                )}
                MenuProps={MenuProps}
              >
                {classifications.map((classification) => (
                  <MenuItem
                    key={classification}
                    value={classification}
                    style={getMultiselectStyles(
                      classification,
                      selectedNonClassifications,
                      theme
                    )}
                  >
                    {classification}
                  </MenuItem>
                ))}
              </Select>
            )}
            name="nonclassifications"
            control={control}
            defaultValue={[]}
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Redshift
          </Typography>
          <TextField
            size="small"
            label="Min"
            name="minRedshift"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
          <TextField
            size="small"
            label="Max"
            name="maxRedshift"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Peak Magnitude
          </Typography>
          <TextField
            size="small"
            label="Min"
            name="minPeakMagnitude"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
          <TextField
            size="small"
            label="Max"
            name="maxPeakMagnitude"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Alias
          </Typography>
          <TextField
            size="small"
            label="Alias"
            type="text"
            name="alias"
            inputRef={register}
            data-testid="alias-text"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Origin
          </Typography>
          <TextField
            size="small"
            label="Origin"
            type="text"
            name="origin"
            inputRef={register}
            data-testid="origin-text"
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Comment
          </Typography>
          <TextField
            size="small"
            label="Comment"
            type="text"
            name="commentsFilter"
            inputRef={register}
            data-testid="comment-text"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Annotation
          </Typography>
          <TextField
            size="small"
            label="Annotation"
            type="text"
            name="annotationsFilter"
            inputRef={register}
            data-testid="annotation-text"
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Comment Author
          </Typography>
          <TextField
            size="small"
            label="Comment Author"
            type="text"
            name="commentsFilterAuthor"
            inputRef={register}
            data-testid="comment-author-text"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Annotation Origin
          </Typography>
          <TextField
            size="small"
            label="Annotation Origin"
            type="text"
            name="annotationsFilterOrigin"
            inputRef={register}
            data-testid="annotation-origin-text"
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Comment Created (UTC)
          </Typography>
          <TextField
            size="small"
            label="Comment After"
            name="commentsFilterAfter"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
          <TextField
            size="small"
            label="Comment Before"
            name="commentsFilterBefore"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Annotation Created (UTC)
          </Typography>
          <TextField
            size="small"
            label="Annotation After"
            name="annotationsFilterAfter"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
          <TextField
            size="small"
            label="Annotation Before"
            name="annotationsFilterBefore"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Latest Magnitude
          </Typography>
          <TextField
            size="small"
            label="Min"
            name="minLatestMagnitude"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
          <TextField
            size="small"
            label="Max"
            name="maxLatestMagnitude"
            type="number"
            inputProps={{
              step: 0.001,
            }}
            inputRef={register}
          />
        </div>
        <div className={classes.formItemRightColumn}>
          <Typography variant="subtitle2" className={classes.title}>
            Which have a...
          </Typography>
          <div className={classes.checkboxGroup}>
            <FormControlLabel
              label="TNS Name"
              labelPlacement="start"
              control={
                <Controller
                  render={({ onChange, value }) => (
                    <Checkbox
                      color="primary"
                      type="checkbox"
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                    />
                  )}
                  name="hasTNSname"
                  control={control}
                  defaultValue={false}
                />
              }
            />
            <FormControlLabel
              label="Spectrum"
              labelPlacement="start"
              control={
                <Controller
                  render={({ onChange, value }) => (
                    <Checkbox
                      color="primary"
                      type="checkbox"
                      onChange={(event) => onChange(event.target.checked)}
                      checked={value}
                    />
                  )}
                  name="hasSpectrum"
                  control={control}
                  defaultValue={false}
                />
              }
            />
          </div>
        </div>
        <div className={classes.formItem}>
          <Typography variant="subtitle2" className={classes.title}>
            Time of Most Recent Spectrum (UTC)
          </Typography>
          <TextField
            size="small"
            label="Spectrum After"
            name="hasSpectrumAfter"
            data-testid="hasSpectrumAfterTest"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
          <TextField
            size="small"
            label="Spectrum Before"
            name="hasSpectrumBefore"
            data-testid="hasSpectrumBeforeTest"
            inputRef={register}
            placeholder="2021-01-01T00:00:00"
          />
        </div>
        <div className={classes.formButtons}>
          <ButtonGroup
            variant="contained"
            color="primary"
            aria-label="contained primary button group"
          >
            <Button variant="contained" color="primary" type="submit">
              Submit
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleClickReset}
            >
              Reset
            </Button>
          </ButtonGroup>
        </div>
      </form>
    </Paper>
  );
};

SourceTableFilterForm.propTypes = {
  handleFilterSubmit: PropTypes.func.isRequired,
};

export default SourceTableFilterForm;
