import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import Paper from "@material-ui/core/Paper";
import Button from "@material-ui/core/Button";
import ButtonGroup from "@material-ui/core/ButtonGroup";
import Checkbox from "@material-ui/core/Checkbox";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import TextField from "@material-ui/core/TextField";
import { makeStyles } from "@material-ui/core/styles";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import { useForm, Controller } from "react-hook-form";

import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import SourceTable from "./SourceTable";

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
  },
  title: {
    margin: "1rem 0rem 0rem 0rem",
  },
  spinner: {
    marginTop: "1rem",
  },
}));

const SourceList = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const sourcesState = useSelector((state) => state.sources.latest);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  useEffect(() => {
    dispatch(sourcesActions.fetchSources());
  }, [dispatch]);

  const { handleSubmit, register, getValues, control, reset } = useForm();

  const onSubmit = (data) => {
    dispatch(sourcesActions.fetchSources(data));
  };

  const handleClickReset = () => {
    reset({ numPerPage: 100 });
    dispatch(sourcesActions.fetchSources());
  };

  const handleSourceTablePagination = (pageNumber, numPerPage) => {
    const data = {
      ...getValues(),
      pageNumber,
      numPerPage,
      totalMatches: sourcesState.totalMatches,
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
                    as={<Checkbox color="primary" type="checkbox" />}
                    name="hasTNSname"
                    control={control}
                    defaultValue={false}
                  />
                }
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
        {!sourcesState.queryInProgress && (
          <Grid item className={classes.tableGrid}>
            <SourceTable
              sources={sourcesState.sources}
              paginateCallback={handleSourceTablePagination}
              totalMatches={sourcesState.totalMatches}
              pageNumber={sourcesState.pageNumber}
              numPerPage={sourcesState.numPerPage}
            />
          </Grid>
        )}
        {sourcesState.queryInProgress && (
          <CircularProgress className={classes.spinner} />
        )}
      </div>
    </Paper>
  );
};

export default SourceList;
