import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import Paper from "@material-ui/core/Paper";
import Button from "@material-ui/core/Button";
import ButtonGroup from "@material-ui/core/ButtonGroup";
import Checkbox from "@material-ui/core/Checkbox";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import TextField from "@material-ui/core/TextField";
import { makeStyles, useTheme } from "@material-ui/core/styles";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import Input from "@material-ui/core/Input";
import Chip from "@material-ui/core/Chip";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import { useForm, Controller } from "react-hook-form";

import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import SourceTable from "./SourceTable";
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
    marginTop: "0.625rem",
  },
  root: {
    display: "flex",
    flexWrap: "wrap",
    "& .MuiTextField-root": {
      margin: theme.spacing(0.2),
      width: "10rem",
    },
  },
  blockWrapper: {
    width: "100%",
    marginBottom: "0.5rem",
  },
  title: {
    margin: "0.5rem 0rem 0rem 0rem",
  },
  spinner: {
    marginTop: "1rem",
  },
}));

const getStyles = (classification, selectedClassifications, theme) => {
  return {
    fontWeight:
      selectedClassifications.indexOf(classification) === -1
        ? theme.typography.fontWeightRegular
        : theme.typography.fontWeightMedium,
  };
};

const SourceList = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const sourcesState = useSelector((state) => state.sources.latest);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const [rowsPerPage, setRowsPerPage] = useState(100);

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
  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) => `${taxonomy.name}: ${option.class}`
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const [selectedClassifications, setSelectedClassifications] = useState([]);

  useEffect(() => {
    dispatch(sourcesActions.fetchSources());
  }, [dispatch]);

  const { handleSubmit, register, getValues, control, reset } = useForm();

  const onSubmit = (formData) => {
    const data = {
      ...formData,
      pageNumber: 1,
      numPerPage: rowsPerPage,
    };
    dispatch(sourcesActions.fetchSources(data));
  };

  const handleClickReset = () => {
    setRowsPerPage(100);
    reset();
    dispatch(
      sourcesActions.fetchSources({
        pageNumber: 1,
        numPerPage: 100,
      })
    );
  };

  const handleSourceTablePagination = (pageNumber, numPerPage) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...getValues(),
      pageNumber,
      numPerPage,
    };
    dispatch(sourcesActions.fetchSources(data));
  };

  const handleSourceTableSorting = (formData) => {
    const data = {
      ...getValues(),
      pageNumber: 1,
      numPerPage: rowsPerPage,
      sortBy: formData.column,
      sortOrder: formData.ascending ? "asc" : "desc",
    };
    dispatch(sourcesActions.fetchSources(data));
  };

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }
  if (!sourcesState.sources) {
    return <CircularProgress />;
  }

  return (
    <Paper elevation={1}>
      <div className={classes.paperDiv}>
        <Typography variant="h6" display="inline">
          Sources
        </Typography>
        <Paper className={classes.paper} variant="outlined">
          <form className={classes.root} onSubmit={handleSubmit(onSubmit)}>
            <div className={classes.blockWrapper}>
              <h4> Filter Sources </h4>
            </div>
            <div className={classes.blockWrapper}>
              <h5 className={classes.title}> Filter by Name or ID </h5>
            </div>
            <div className={classes.blockWrapper}>
              <TextField
                fullWidth
                label="Source ID/Name"
                name="sourceID"
                inputRef={register}
              />
            </div>

            <div className={classes.blockWrapper}>
              <h5 className={classes.title}> Filter by Position </h5>
            </div>
            <div className={classes.blockWrapper}>
              <TextField
                size="small"
                label="RA (degrees)"
                name="ra"
                inputRef={register}
              />
              <TextField
                size="small"
                label="Dec (degrees)"
                name="dec"
                inputRef={register}
              />
              <TextField
                size="small"
                label="Radius (degrees)"
                name="radius"
                inputRef={register}
              />
            </div>
            <div className={classes.blockWrapper}>
              <h5 className={classes.title}>
                Filter by Time Last Detected (UTC)
              </h5>
            </div>
            <div className={classes.blockWrapper}>
              <TextField
                size="small"
                label="Start Date"
                name="startDate"
                inputRef={register}
                placeholder="2012-08-30T00:00:00"
              />
              <TextField
                size="small"
                label="End Date"
                name="endDate"
                inputRef={register}
                placeholder="2012-08-30T00:00:00"
              />
            </div>
            <div className={classes.blockWrapper}>
              <h5 className={classes.title}> Filter by Simbad Class </h5>
            </div>
            <div className={classes.blockWrapper}>
              <TextField
                size="small"
                label="Class Name"
                type="text"
                name="simbadClass"
                inputRef={register}
              />
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
            </div>
            <div className={classes.blockWrapper}>
              <h5 className={classes.title}> Filter by Classification </h5>
            </div>
            <div className={classes.blockWrapper}>
              <Controller
                render={({ onChange, value }) => (
                  <Select
                    labelId="classifications-select-label"
                    id="classifications-select"
                    multiple
                    value={value}
                    onChange={(event) => {
                      setSelectedClassifications(event.target.value);
                      onChange(event.target.value);
                    }}
                    input={<Input id="classifications-select" />}
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
                )}
                name="classifications"
                control={control}
                defaultValue={[]}
              />
            </div>
            <div className={classes.blockWrapper}>
              <ButtonGroup
                variant="contained"
                color="primary"
                aria-label="contained primary button group"
              >
                <Button
                  variant="contained"
                  color="primary"
                  type="submit"
                  disabled={sourcesState.queryInProgress}
                >
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
        {sourcesState.sources && (
          <Grid item className={classes.tableGrid}>
            <SourceTable
              sources={sourcesState.sources}
              paginateCallback={handleSourceTablePagination}
              totalMatches={sourcesState.totalMatches}
              pageNumber={sourcesState.pageNumber}
              numPerPage={sourcesState.numPerPage}
              sortingCallback={handleSourceTableSorting}
            />
          </Grid>
        )}
        {!sourcesState.sources && (
          <CircularProgress className={classes.spinner} />
        )}
      </div>
    </Paper>
  );
};

export default SourceList;
