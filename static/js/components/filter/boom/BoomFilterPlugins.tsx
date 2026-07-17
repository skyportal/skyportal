import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import { UnifiedBuilderProvider } from "../../../contexts/UnifiedBuilderContext";
import FilterBuilderContent from "./FilterBuilderContent";
import AnnotationBuilderContent from "./AnnotationBuilderContent";

import { useForm, Controller } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import * as filterActions from "../../../ducks/boom_filter";
import { useGetGroupsQuery } from "../../../ducks/groups";

interface BoomFilterPluginsProps {
  // Unused by the implementation (groups come from useGetGroupsQuery); optional
  // so the component can mount from a route without a group prop.
  group?: any;
}

const useStyles = makeStyles()((theme) => ({
  pre: {
    lineHeight: 8,
  },
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  nested: {
    paddingLeft: theme.spacing(1),
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  accordion_details: {
    flexDirection: "column",
  },
  appBar: {
    position: "relative",
  },
  button_add: {
    marginRight: 10,
    height: "3.5rem",
  },
  divider: {
    width: "100%",
    height: 2,
    backgroundColor: "rgba(0, 0, 0, .125)",
    margin: "1rem 0",
  },
  infoLine: {
    // Get its own line
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    padding: "0.25rem 0",
  },
  formControl: {
    marginLeft: theme.spacing(0.5),
    marginTop: theme.spacing(1),
    minWidth: "12rem",
  },
  marginLeft: {
    marginLeft: theme.spacing(2),
  },
  marginTop: {
    marginTop: theme.spacing(2),
  },
  root: {
    minWidth: "18rem",
  },
  bullet: {
    display: "inline-block",
    margin: "0 2px",
    transform: "scale(0.8)",
  },
  filter_details: {
    marginTop: "1rem",
    marginBottom: "1rem",
    fontSize: "0.875rem",
  },
  big_font: {
    fontSize: "1rem",
  },
  pos: {
    marginBottom: "0.75rem",
  },
  header: {
    paddingBottom: 10,
  },
}));

const BoomFilterPlugins = (_props: BoomFilterPluginsProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { handleSubmit, setValue, control } = useForm();

  const theme = useTheme();

  const filter_v = useAppSelector((state: any) => state.boom_filter_v);

  const { fid } = useParams();
  const loadedId = useAppSelector((state: any) => state.boom_filter_v?.id);

  const { data: groupsData } = useGetGroupsQuery();
  const allGroups = groupsData?.all;

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((g: any) => {
    groupLookUp[g.id] = g;
  });

  const [panelboomExpanded, setPanelboomExpanded] = useState<any>(true);

  const handlePanelboomChange =
    (panel: any) => (_event: any, isExpanded: any) => {
      setPanelboomExpanded(isExpanded ? panel : false);
    };

  const handleChangeActiveFilter = async (event: any) => {
    const active_target = event.target.checked;
    const result: any = await dispatch(
      filterActions.editFilterVersion({
        filter_id: filter_v.id,
        active: active_target,
        active_fid: filter_v.active_fid,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification(`Set active to ${active_target}`));
    }
    dispatch(filterActions.fetchFilterVersion(fid));
  };

  const handleFidChange = async (event: any) => {
    const activeFidTarget = event.target.value;
    const result: any = await dispatch(
      filterActions.editFilterVersion({
        filter_id: filter_v.id,
        active: filter_v.active,
        active_fid: activeFidTarget,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification(`Set active filter ID to ${activeFidTarget}`));
    }
    dispatch(filterActions.fetchFilterVersion(fid));
  };

  // forms
  const [inlineNewVersion, setInlineNewVersion] = React.useState(false);
  const [showAnnotationBuilder, setShowAnnotationBuilder] = useState(false);

  useEffect(() => {
    let newPipeline: any = (filter_v?.fv || []).filter(
      (fv: any) => fv.fid === filter_v.active_fid,
    );
    if (newPipeline.length > 0) {
      newPipeline = newPipeline[0].pipeline;
    } else {
      newPipeline = "";
    }
    if (filter_v?.fv?.length > 0 && filter_v?.active_fid) {
      setValue("pipeline", newPipeline);
    }
  }, [filter_v, setValue]);

  // save new filter version
  const onSubmitSaveFilterVersion = async (data: any) => {
    const result: any = await dispatch(
      filterActions.updateGroupFilter(filter_v.id, data.pipeline),
    );
    if (result.status === "success") {
      dispatch(showNotification(`Saved new filter version`));
      setInlineNewVersion(false);
      setShowAnnotationBuilder(false);
    }
    dispatch(filterActions.fetchFilterVersion(fid));
  };

  const handleNew = () => {
    if (!inlineNewVersion) {
      // Only fetch when opening the builder
      dispatch(filterActions.fetchFilterVersion(fid));
    }
    setInlineNewVersion(!inlineNewVersion);
  };

  useEffect(() => {
    if (loadedId !== fid) {
      dispatch(filterActions.fetchFilterVersion(fid));
    }
  }, [fid, loadedId, dispatch]);

  // renders
  if (!filter_v) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  return (
    <div style={{ overflow: "visible" }}>
      <Accordion
        expanded={panelboomExpanded}
        onChange={handlePanelboomChange(true)}
        sx={{ overflow: "visible" }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel-streams-content"
          id="panel-header"
          style={{ borderBottom: "1px solid rgba(0, 0, 0, .125)" }}
        >
          <Typography className={classes.heading}>
            Boom filter details
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          className={classes.accordion_details}
          sx={{ overflow: "visible" }}
        >
          {inlineNewVersion ? (
            // Inline new version mode - show only filter info and builder
            <UnifiedBuilderProvider
              mode={showAnnotationBuilder ? "annotation" : "filter"}
            >
              <div
                style={{
                  width: "100%",
                  maxWidth: "100%",
                  overflow: "hidden",
                  boxSizing: "border-box",
                }}
              >
                {/* Filter basic info */}
                {filter_v?.fv && (
                  <div style={{ marginBottom: "2rem" }}>
                    <Typography variant="h6" gutterBottom>
                      Creating New Filter Version
                    </Typography>
                    <div className={classes.infoLine}>
                      <FormControlLabel
                        // className={classes.formControl}
                        style={{
                          marginLeft: theme.spacing(0.5),
                          marginTop: theme.spacing(1),
                        }}
                        control={
                          <Switch
                            checked={filter_v.active}
                            size="small"
                            onChange={handleChangeActiveFilter}
                            name="filterActive"
                          />
                        }
                        label="Active"
                      />
                      <Button
                        variant="outlined"
                        color="primary"
                        onClick={() => {
                          setInlineNewVersion(false);
                          setShowAnnotationBuilder(false);
                        }}
                        style={{ marginRight: "1rem" }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {/* Inline Filter Builder */}
                <Box
                  sx={{
                    width: "100%",
                    maxWidth: "100%",
                    overflow: "visible", // Allow dropdowns to overflow
                    boxSizing: "border-box",
                    mt: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    backgroundColor: "background.paper",
                    // Responsive sizing
                    maxHeight: { xs: "70vh", md: "80vh" },
                    overflowY: "auto", // Only hide vertical overflow for scrolling
                  }}
                >
                  <form
                    id="inline-filter-form"
                    onSubmit={handleSubmit(onSubmitSaveFilterVersion)}
                  >
                    <Controller
                      render={() => (
                        <>
                          <Box
                            sx={{
                              display: showAnnotationBuilder ? "block" : "none",
                              width: "100%",
                              maxWidth: "100%",
                              overflow: "visible",
                              "& > .MuiBox-root": {
                                width: "100% !important",
                                maxWidth: "100% !important",
                                minHeight: "auto !important",
                                padding: {
                                  xs: "0.5rem !important",
                                  md: "1rem !important",
                                },
                                boxSizing: "border-box !important",
                              },
                              "& h2": {
                                fontSize: {
                                  xs: "1.125rem !important",
                                  md: "1.25rem !important",
                                },
                                marginBottom: "1rem !important",
                              },
                              "& .MuiButton-root": {
                                fontSize: {
                                  xs: "0.75rem !important",
                                  md: "0.875rem !important",
                                },
                              },
                            }}
                          >
                            <AnnotationBuilderContent
                              onBackToFilterBuilder={() =>
                                setShowAnnotationBuilder(false)
                              }
                              {...({
                                filter: filter_v,
                                setInlineNewVersion,
                                setShowAnnotationBuilder,
                              } as any)}
                            />
                          </Box>
                          <Box
                            sx={{
                              display: showAnnotationBuilder ? "none" : "block",
                              width: "100%",
                              maxWidth: "100%",
                              overflow: "visible",
                              "& > .MuiBox-root": {
                                width: "100% !important",
                                maxWidth: "100% !important",
                                minHeight: "auto !important",
                                padding: {
                                  xs: "0.5rem !important",
                                  md: "1rem !important",
                                },
                                boxSizing: "border-box !important",
                              },
                              "& h2": {
                                fontSize: {
                                  xs: "1.125rem !important",
                                  md: "1.25rem !important",
                                },
                                marginBottom: "1rem !important",
                              },
                              "& .MuiButton-root": {
                                fontSize: {
                                  xs: "0.75rem !important",
                                  md: "0.875rem !important",
                                },
                              },
                            }}
                          >
                            <FilterBuilderContent
                              onToggleAnnotationBuilder={() =>
                                setShowAnnotationBuilder(true)
                              }
                              filter={filter_v}
                              setInlineNewVersion={setInlineNewVersion}
                              setShowAnnotationBuilder={
                                setShowAnnotationBuilder
                              }
                            />
                          </Box>
                        </>
                      )}
                      name="pipeline"
                      control={control}
                    />
                  </form>
                </Box>
              </div>
            </UnifiedBuilderProvider>
          ) : (
            // Normal mode - show all controls
            <>
              {filter_v?.fv && (
                <div className={classes.infoLine}>
                  <FormControlLabel
                    className={classes.formControl}
                    control={
                      <Switch
                        checked={filter_v.active}
                        size="small"
                        onChange={handleChangeActiveFilter}
                        name="filterActive"
                      />
                    }
                    label="Active"
                  />
                </div>
              )}
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "end",
                  gap: "1rem",
                }}
              >
                {filter_v?.fv && (
                  <FormControl className={classes.formControl}>
                    <InputLabel id="alert-stream-select-required-label">
                      Active version
                    </InputLabel>
                    <Select
                      disabled={!filter_v.active}
                      labelId="alert-stream-select-required-label"
                      id="alert-stream-select"
                      value={filter_v.active_fid}
                      onChange={handleFidChange}
                      className={classes.marginTop}
                    >
                      {filter_v.fv.map((fv: any) => (
                        <MenuItem key={fv.fid} value={fv.fid}>
                          {fv.fid}: {fv?.created_at?.toString().slice(0, 19)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
                <>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleNew}
                    className={classes.button_add}
                  >
                    {inlineNewVersion ? "Cancel new version" : "Show Filter"}
                  </Button>
                </>
              </div>
            </>
          )}
        </AccordionDetails>
      </Accordion>
    </div>
  );
};

export default BoomFilterPlugins;
