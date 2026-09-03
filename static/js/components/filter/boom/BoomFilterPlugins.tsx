import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import { UnifiedBuilderProvider } from "../../../contexts/UnifiedBuilderContext";
import FilterBuilderContent from "./FilterBuilderContent";
import AnnotationBuilderContent from "./AnnotationBuilderContent";
import BoomFilterFollowupConfig from "./BoomFilterFollowupConfig";
import FilterVersionDiff from "./FilterVersionDiff";

import { useForm, Controller } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../../types/hooks";
import {
  useBoomFilterVersion,
  useEditBoomFilterVersionMutation,
  useUpdateBoomGroupFilterMutation,
  useUpdateBoomFilterFlagsMutation,
  useValidateBoomFilterMutation,
} from "../../../ducks/boom_filter";
import { useGetGroupsQuery } from "../../../ducks/groups";
import { useGetGroupQuery } from "../../../ducks/group";
import { useDeleteDefaultFollowupRequestMutation } from "../../../ducks/default_followup_requests";
import { useGetProfileQuery } from "../../../ducks/profile";

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

  const { data: filter_v = {}, refetch: refetchFilterVersion } =
    useBoomFilterVersion();
  const [editFilterVersion] = useEditBoomFilterVersionMutation();
  const [updateGroupFilter] = useUpdateBoomGroupFilterMutation();
  const [updateFilterFlags] = useUpdateBoomFilterFlagsMutation();
  const [validateFilter] = useValidateBoomFilterMutation();
  const { data: profile } = useGetProfileQuery();
  const isAdmin = (profile?.permissions ?? []).includes("System admin");
  const [validating, setValidating] = useState(false);

  // A filter version may be activated only once it has passed validation for
  // that fid (or by an admin). Verdicts are stored per fid so each version keeps
  // its own result; fall back to the legacy single-slot record for old data.
  const boomValidations = filter_v?.altdata?.boom?.validations;
  const legacyValidation = filter_v?.altdata?.boom?.validation;
  const validation =
    boomValidations?.[filter_v?.active_fid] ??
    (legacyValidation?.fid === filter_v?.active_fid
      ? legacyValidation
      : undefined);
  const isValidated = !!validation?.passed;

  const { data: groupsData } = useGetGroupsQuery();
  const allGroups = groupsData?.all;

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((g: any) => {
    groupLookUp[g.id] = g;
  });

  // Auto-actions run when an object passes: save to the filter's group (skipping
  // objects already in an ignore/junk group), annotate, and/or trigger followup.
  // Stored in the filter's altdata.
  const autoSaveOn = !!filter_v?.altdata?.autoSave;
  const autoAnnotateOn = !!filter_v?.altdata?.autoAnnotate;
  const autoFollowupOn = !!filter_v?.altdata?.autoFollowup;
  const ignoreGroupIds: number[] =
    filter_v?.altdata?.autoSaveIgnoreGroupIds ?? [];
  const handleFlagToggle =
    (flag: "autoSave" | "autoAnnotate" | "autoFollowup") =>
    async (checked: boolean) => {
      await updateFilterFlags({ filter_id: filter_v.id, [flag]: checked });
      refetchFilterVersion();
    };
  const handleIgnoreGroupsChange = async (ids: number[]) => {
    await updateFilterFlags({
      filter_id: filter_v.id,
      autoSaveIgnoreGroupIds: ids,
    });
    refetchFilterVersion();
  };

  // Auto-save attribution + comment. Members come from the filter's own group.
  const saverId: number | "" = filter_v?.altdata?.autoSaveSaverId ?? "";
  const { data: filterGroup } = useGetGroupQuery(filter_v?.group_id, {
    skip: !autoSaveOn || !filter_v?.group_id,
  });
  const groupMembers: any[] = (filterGroup as any)?.users ?? [];
  const handleSaverChange = async (id: number | "") => {
    await updateFilterFlags({
      filter_id: filter_v.id,
      autoSaveSaverId: id === "" ? null : id,
    });
    refetchFilterVersion();
  };
  const handleCommentBlur = async (text: string) => {
    if ((filter_v?.altdata?.autoSaveComment ?? "") === text) return;
    await updateFilterFlags({ filter_id: filter_v.id, autoSaveComment: text });
    refetchFilterVersion();
  };
  const handleIgnoreRadiusBlur = async (val: string) => {
    const parsed = val.trim() === "" ? null : Number(val);
    if ((filter_v?.altdata?.autoSaveIgnoreRadius ?? null) === parsed) return;
    await updateFilterFlags({
      filter_id: filter_v.id,
      autoSaveIgnoreRadius: parsed,
    });
    refetchFilterVersion();
  };

  // Auto-followup is backed by a skyportal DefaultFollowupRequest scoped to this
  // filter's group; the flag reflects whether one is linked.
  const autoFollowupDefaultId: number | null =
    filter_v?.altdata?.autoFollowupDefaultId ?? null;
  const [followupConfigOpen, setFollowupConfigOpen] = useState(false);
  const [deleteDefaultFollowup] = useDeleteDefaultFollowupRequestMutation();
  const handleAutoFollowupToggle = async (checked: boolean) => {
    if (checked) {
      // Reveal the config; the flag is set once a default request is created.
      setFollowupConfigOpen(true);
      return;
    }
    if (autoFollowupDefaultId) {
      try {
        await deleteDefaultFollowup(autoFollowupDefaultId).unwrap();
      } catch {
        // notification handled by baseQuery
      }
    }
    await updateFilterFlags({
      filter_id: filter_v.id,
      autoFollowup: false,
      autoFollowupDefaultId: null,
    });
    setFollowupConfigOpen(false);
    refetchFilterVersion();
  };
  const handleFollowupLinked = async (id: number | null) => {
    await updateFilterFlags({
      filter_id: filter_v.id,
      autoFollowup: id != null,
      autoFollowupDefaultId: id,
    });
    if (id != null) setFollowupConfigOpen(false);
    refetchFilterVersion();
  };

  const [panelboomExpanded, setPanelboomExpanded] = useState<any>(true);

  const handlePanelboomChange =
    (panel: any) => (_event: any, isExpanded: any) => {
      setPanelboomExpanded(isExpanded ? panel : false);
    };

  const handleChangeActiveFilter = async (event: any) => {
    const active_target = event.target.checked;
    const result: any = await editFilterVersion({
      filter_id: filter_v.id,
      active: active_target,
      active_fid: filter_v.active_fid,
    });
    if (!result.error) {
      dispatch(showNotification(`Set active to ${active_target}`));
    }
    refetchFilterVersion();
  };

  const handleFidChange = async (event: any) => {
    const activeFidTarget = event.target.value;
    const result: any = await editFilterVersion({
      filter_id: filter_v.id,
      active: filter_v.active,
      active_fid: activeFidTarget,
    });
    if (!result.error) {
      dispatch(showNotification(`Set active filter ID to ${activeFidTarget}`));
    }
    refetchFilterVersion();
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const result: any = await validateFilter({
        filter_id: filter_v.id,
        fid: filter_v.active_fid,
      });
      const payload = result?.data?.data ?? result?.data;
      if (result?.error) {
        dispatch(showNotification("Validation request failed.", "error"));
      } else if (payload?.passed) {
        dispatch(
          showNotification("Filter validated — it can now be activated."),
        );
      } else {
        dispatch(
          showNotification(
            `Filter did not pass validation: ${payload?.message ?? "too permissive"}`,
            "warning",
          ),
        );
      }
    } finally {
      setValidating(false);
      refetchFilterVersion();
    }
  };

  const activationControls = (
    <Box
      sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}
    >
      <Button
        variant="outlined"
        size="small"
        onClick={handleValidate}
        disabled={validating}
        startIcon={validating ? <CircularProgress size={14} /> : undefined}
      >
        {validating ? "Validating…" : "Validate"}
      </Button>
      <Tooltip
        title={
          !filter_v.active && !isValidated && !isAdmin
            ? "Validate this version before activating"
            : ""
        }
      >
        <span>
          <FormControlLabel
            control={
              <Switch
                checked={!!filter_v.active}
                size="small"
                onChange={handleChangeActiveFilter}
                name="filterActive"
                // deactivating is always allowed; only activating needs validation
                disabled={!filter_v.active && !isValidated && !isAdmin}
              />
            }
            label="Active"
          />
        </span>
      </Tooltip>
      {validating ? (
        <Typography variant="caption" color="textSecondary">
          Running the filter over a night of alerts — this can take a while.
        </Typography>
      ) : validation ? (
        <Tooltip
          title={!isValidated && validation.message ? validation.message : ""}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.5,
              minWidth: 0,
            }}
          >
            {isValidated ? (
              <CheckCircleIcon fontSize="small" color="success" />
            ) : (
              <CancelIcon fontSize="small" color="error" />
            )}
            <Typography
              variant="caption"
              color={isValidated ? "success.main" : "error"}
            >
              {isValidated
                ? "Validated"
                : validation.message
                  ? "Validation failed (hover for details)"
                  : "Validation failed"}
            </Typography>
          </Box>
        </Tooltip>
      ) : !filter_v.active ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <HelpOutlineIcon fontSize="small" color="disabled" />
          <Typography variant="caption" color="textSecondary">
            Not validated for this version
          </Typography>
        </Box>
      ) : null}
    </Box>
  );

  const autoSaveControls = (
    <Box
      sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}
    >
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={autoSaveOn}
            onChange={(e) => handleFlagToggle("autoSave")(e.target.checked)}
          />
        }
        label="Auto-save to group"
      />
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={autoAnnotateOn}
            onChange={(e) => handleFlagToggle("autoAnnotate")(e.target.checked)}
          />
        }
        label="Auto-annotate"
      />
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={autoFollowupOn || followupConfigOpen}
            onChange={(e) => handleAutoFollowupToggle(e.target.checked)}
          />
        }
        label="Auto-trigger follow-up"
      />
      {autoSaveOn && (
        <FormControl size="small" sx={{ minWidth: 240 }}>
          <InputLabel id={`ignore-groups-${filter_v.id}`}>
            Skip if already in
          </InputLabel>
          <Select
            multiple
            labelId={`ignore-groups-${filter_v.id}`}
            label="Skip if already in"
            value={ignoreGroupIds}
            onChange={(e) =>
              handleIgnoreGroupsChange(e.target.value as number[])
            }
            renderValue={(sel) =>
              (sel as number[])
                .map((id) => groupLookUp[id]?.name ?? id)
                .join(", ")
            }
          >
            {allGroups?.map((g: any) => (
              <MenuItem key={g.id} value={g.id}>
                {g.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {autoSaveOn && (
        <TextField
          size="small"
          type="number"
          sx={{ minWidth: 160 }}
          label="Junk skip radius (arcsec)"
          placeholder="2"
          helperText="Default 2″; 0 = exact match only"
          key={`ignore-radius-${filter_v.id}-${filter_v?.altdata?.autoSaveIgnoreRadius ?? ""}`}
          defaultValue={filter_v?.altdata?.autoSaveIgnoreRadius ?? ""}
          onBlur={(e) => handleIgnoreRadiusBlur(e.target.value)}
        />
      )}
      {autoSaveOn && (
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id={`saver-${filter_v.id}`}>Save as</InputLabel>
          <Select
            labelId={`saver-${filter_v.id}`}
            label="Save as"
            value={saverId}
            onChange={(e) => handleSaverChange(e.target.value as number | "")}
          >
            <MenuItem value="">
              <em>Bot (default)</em>
            </MenuItem>
            {groupMembers.map((u: any) => (
              <MenuItem key={u.id} value={u.id}>
                {u.username}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {autoSaveOn && (
        <TextField
          size="small"
          sx={{ minWidth: 240 }}
          label="Save comment"
          key={`comment-${filter_v.id}-${filter_v?.altdata?.autoSaveComment ?? ""}`}
          defaultValue={filter_v?.altdata?.autoSaveComment ?? ""}
          onBlur={(e) => handleCommentBlur(e.target.value)}
        />
      )}
    </Box>
  );

  // forms
  const location = useLocation();
  // Read once at mount, during render (before PageTourProvider's effect can
  // clear location.state) so the "filter" page tour's targets are already
  // mounted when it starts polling for them.
  const [inlineNewVersion, setInlineNewVersion] = React.useState(
    () => (location.state as any)?.tour === "filter",
  );
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
    const result: any = await updateGroupFilter({
      filter_id: filter_v.id,
      altdata: data.pipeline,
    });
    if (!result.error) {
      dispatch(showNotification(`Saved new filter version`));
      setInlineNewVersion(false);
      setShowAnnotationBuilder(false);
    }
    refetchFilterVersion();
  };

  const handleNew = () => {
    if (!inlineNewVersion) {
      // Only fetch when opening the builder
      refetchFilterVersion();
    }
    setInlineNewVersion(!inlineNewVersion);
  };

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
                      {activationControls}
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
                <div className={classes.infoLine}>{activationControls}</div>
              )}
              {filter_v?.fv && (
                <div className={classes.infoLine}>{autoSaveControls}</div>
              )}
              {filter_v?.fv && (autoFollowupOn || followupConfigOpen) && (
                <div className={classes.infoLine}>
                  <BoomFilterFollowupConfig
                    filterId={filter_v.id}
                    groupId={filter_v.group_id}
                    existingDefaultId={autoFollowupDefaultId}
                    onLinked={handleFollowupLinked}
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
                {filter_v?.fv && (
                  <FilterVersionDiff
                    versions={filter_v.fv}
                    activeFid={filter_v.active_fid}
                    validations={filter_v?.altdata?.boom?.validations}
                  />
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
