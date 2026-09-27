import { useEffect, useRef, useState } from "react";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
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
import GcnCrossmatchPlugin from "../GcnCrossmatchPlugin";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../../types/hooks";
import {
  useBoomFilterVersion,
  useEditBoomFilterVersionMutation,
  useUpdateBoomFilterFlagsMutation,
  useValidateBoomFilterMutation,
} from "../../../ducks/boom_filter";
import { useGetGroupsQuery } from "../../../ducks/groups";
import { useGetGroupQuery } from "../../../ducks/group";
import { useDeleteDefaultFollowupRequestMutation } from "../../../ducks/default_followup_requests";
import { useGetProfileQuery } from "../../../ducks/profile";

const builderSx = {
  "& > .MuiBox-root": {
    width: "100% !important",
    maxWidth: "100% !important",
    minHeight: "auto !important",
    padding: { xs: "0.5rem !important", md: "1rem !important" },
    boxSizing: "border-box !important",
  },
  "& .MuiButton-root": {
    fontSize: { xs: "0.75rem !important", md: "0.875rem !important" },
  },
};

const nestedSx = { borderLeft: 3, borderColor: "primary.light", pl: 2 };

const Section = ({
  title,
  nested = false,
  children,
}: {
  title: string;
  nested?: boolean;
  children: any;
}) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      gap: 1,
      ...(nested && nestedSx),
    }}
  >
    <Typography variant="subtitle2" color="text.secondary">
      {title}
    </Typography>
    <Box
      sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}
    >
      {children}
    </Box>
  </Box>
);

const ToggleWithHelp = ({
  label,
  help,
  checked,
  disabled,
  loading,
  onChange,
}: any) => (
  <Tooltip title={help}>
    <FormControlLabel
      control={
        <Switch
          size="small"
          checked={checked}
          disabled={disabled || loading}
          onChange={(e) => onChange(e.target.checked)}
        />
      }
      label={
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {label}
          {loading && <CircularProgress size={14} />}
        </Box>
      }
    />
  </Tooltip>
);

const BoomFilterPlugins = () => {
  const dispatch = useAppDispatch();

  const { data: filter_v = {}, refetch: refetchFilterVersion } =
    useBoomFilterVersion();
  const [editFilterVersion] = useEditBoomFilterVersionMutation();
  const [updateFilterFlags] = useUpdateBoomFilterFlagsMutation();
  const [validateFilter, { isLoading: startingValidation }] =
    useValidateBoomFilterMutation();
  const [deleteDefaultFollowup] = useDeleteDefaultFollowupRequestMutation();
  const { data: profile } = useGetProfileQuery();
  const allGroups = useGetGroupsQuery().data?.all ?? [];
  const [followupConfigOpen, setFollowupConfigOpen] = useState(false);
  const [showAnnotationBuilder, setShowAnnotationBuilder] = useState(false);
  const [tab, setTab] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  const altdata = filter_v.altdata ?? {};
  const isAdmin = (profile?.permissions ?? []).includes("System admin");
  // Legacy single-slot verdict, for versions validated before per-fid storage.
  const validation =
    altdata.boom?.validations?.[filter_v.active_fid] ??
    (altdata.boom?.validation?.fid === filter_v.active_fid
      ? altdata.boom?.validation
      : undefined);
  const isValidated = !!validation?.passed;
  const validating = startingValidation || !!validation?.pending;
  useBoomFilterVersion({ pollingInterval: validation?.pending ? 5000 : 0 });

  const wasPending = useRef(false);
  useEffect(() => {
    if (validation?.pending) {
      wasPending.current = true;
    } else if (wasPending.current && validation) {
      wasPending.current = false;
      dispatch(
        validation.passed
          ? showNotification("Filter validated: it can now be activated.")
          : showNotification(
              `Filter did not pass validation: ${validation.message ?? "too permissive"}`,
              "warning",
            ),
      );
    }
  }, [validation, dispatch]);
  const canActivate = filter_v.active || isValidated || isAdmin;
  const autoSaveOn = !!filter_v.autosave;
  const autoFollowupDefaultId: number | null =
    altdata.autoFollowupDefaultId ?? null;

  const { data: filterGroup } = useGetGroupQuery(filter_v.group_id, {
    skip: !autoSaveOn || !filter_v.group_id,
  });

  const updateFlags = async (flags: Record<string, any>) => {
    setBusy(Object.keys(flags)[0] ?? null);
    await updateFilterFlags({ filter_id: filter_v.id, ...flags });
    await refetchFilterVersion();
    setBusy(null);
  };

  const updateOnBlur = (key: string, value: any) => {
    if ((altdata[key] ?? null) !== value) updateFlags({ [key]: value });
  };

  const editVersion = async (
    patch: { active?: boolean; active_fid?: string },
    message: string,
  ) => {
    setBusy(Object.keys(patch)[0] ?? null);
    const result: any = await editFilterVersion({
      filter_id: filter_v.id,
      active: filter_v.active,
      active_fid: filter_v.active_fid,
      ...patch,
    });
    if (!result.error) dispatch(showNotification(message));
    await refetchFilterVersion();
    setBusy(null);
  };

  const handleAutoFollowupToggle = async (checked: boolean) => {
    // The flag is only set once a default request is created in the config.
    if (checked) {
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
    setFollowupConfigOpen(false);
    updateFlags({ autoFollowup: false, autoFollowupDefaultId: null });
  };

  const handleValidate = async () => {
    try {
      await validateFilter({
        filter_id: filter_v.id,
        fid: filter_v.active_fid,
      }).unwrap();
      dispatch(
        showNotification("Validation started, this can take a few minutes."),
      );
    } catch {
      // notification handled by baseQuery
    }
    refetchFilterVersion();
  };

  const validationChip = validating ? (
    <Chip
      size="small"
      icon={<CircularProgress size={12} />}
      label="Validating…"
    />
  ) : validation ? (
    <Tooltip title={isValidated ? "" : (validation.message ?? "")}>
      <Chip
        size="small"
        color={isValidated ? "success" : "error"}
        icon={isValidated ? <CheckCircleIcon /> : <CancelIcon />}
        label={isValidated ? "Validated" : "Validation failed"}
      />
    </Tooltip>
  ) : (
    !filter_v.active && (
      <Chip
        size="small"
        variant="outlined"
        icon={<HelpOutlineIcon />}
        label="Not validated"
      />
    )
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {filter_v.fv && (
        <Paper
          variant="outlined"
          sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}
        >
          <Section title="Version">
            <TextField
              select
              size="small"
              label="Active version"
              disabled={!filter_v.active || busy === "active_fid"}
              value={filter_v.active_fid}
              onChange={(e) =>
                editVersion(
                  { active_fid: e.target.value },
                  `Set active filter ID to ${e.target.value}`,
                )
              }
              sx={{ minWidth: "12rem" }}
            >
              {filter_v.fv.map((fv: any) => (
                <MenuItem key={fv.fid} value={fv.fid}>
                  {fv.fid}: {fv.created_at?.toString().slice(0, 19)}
                </MenuItem>
              ))}
            </TextField>
            <FilterVersionDiff
              versions={filter_v.fv}
              activeFid={filter_v.active_fid}
              validations={altdata.boom?.validations}
            />
            <Box
              sx={{ ml: "auto", display: "flex", alignItems: "center", gap: 2 }}
            >
              {validationChip}
              <Tooltip title="Run this version over a night of alerts to check it is not too permissive. This can take a few minutes.">
                <span>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleValidate}
                    disabled={validating}
                  >
                    Validate
                  </Button>
                </span>
              </Tooltip>
              <ToggleWithHelp
                label="Active"
                help={
                  canActivate
                    ? "Run this version on live alerts"
                    : "Validate this version before activating it"
                }
                checked={!!filter_v.active}
                disabled={!canActivate}
                loading={busy === "active"}
                onChange={(active: boolean) =>
                  editVersion({ active }, `Set active to ${active}`)
                }
              />
            </Box>
          </Section>
          <Divider />
          <Section title="When an object passes">
            <ToggleWithHelp
              label="Auto-save to group"
              help="Save it as a source in this filter's group"
              checked={autoSaveOn}
              loading={busy === "autoSave"}
              onChange={(autoSave: boolean) => updateFlags({ autoSave })}
            />
            <ToggleWithHelp
              label="Auto-annotate"
              help="Attach the annotations defined in the annotation builder"
              checked={!!altdata.autoAnnotate}
              loading={busy === "autoAnnotate"}
              onChange={(autoAnnotate: boolean) =>
                updateFlags({ autoAnnotate })
              }
            />
            <ToggleWithHelp
              label="Auto-trigger follow-up"
              help="Submit the default follow-up request configured below"
              checked={!!altdata.autoFollowup || followupConfigOpen}
              loading={busy === "autoFollowup"}
              onChange={handleAutoFollowupToggle}
            />
          </Section>
          {autoSaveOn && (
            <Section title="Auto-save options" nested>
              <TextField
                select
                size="small"
                label="Skip if already in"
                value={altdata.autoSaveIgnoreGroupIds ?? []}
                onChange={(e) =>
                  updateFlags({ autoSaveIgnoreGroupIds: e.target.value })
                }
                slotProps={{
                  select: {
                    multiple: true,
                    renderValue: (ids: any) =>
                      ids
                        .map(
                          (id: number) =>
                            allGroups.find((g: any) => g.id === id)?.name ?? id,
                        )
                        .join(", "),
                  },
                }}
                sx={{ minWidth: 240 }}
              >
                {allGroups.map((g: any) => (
                  <MenuItem key={g.id} value={g.id}>
                    {g.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                type="number"
                label="Junk skip radius (arcsec)"
                placeholder="2"
                helperText="Default 2″; 0 = exact match only"
                key={`radius-${altdata.autoSaveIgnoreRadius ?? ""}`}
                defaultValue={altdata.autoSaveIgnoreRadius ?? ""}
                onBlur={(e) =>
                  updateOnBlur(
                    "autoSaveIgnoreRadius",
                    e.target.value.trim() === ""
                      ? null
                      : Number(e.target.value),
                  )
                }
                sx={{ minWidth: 160 }}
              />
              <TextField
                select
                size="small"
                label="Save as"
                value={altdata.autoSaveSaverId ?? ""}
                onChange={(e) =>
                  updateFlags({ autoSaveSaverId: e.target.value || null })
                }
                sx={{ minWidth: 180 }}
              >
                <MenuItem value="">
                  <em>Bot (default)</em>
                </MenuItem>
                {((filterGroup as any)?.users ?? []).map((u: any) => (
                  <MenuItem key={u.id} value={u.id}>
                    {u.username}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                label="Save comment"
                key={`comment-${altdata.autoSaveComment ?? ""}`}
                defaultValue={altdata.autoSaveComment ?? ""}
                onBlur={(e) =>
                  updateOnBlur("autoSaveComment", e.target.value || null)
                }
                sx={{ minWidth: 240 }}
              />
            </Section>
          )}
          {(altdata.autoFollowup || followupConfigOpen) && (
            <Box sx={nestedSx}>
              <BoomFilterFollowupConfig
                filterId={filter_v.id}
                groupId={filter_v.group_id}
                existingDefaultId={autoFollowupDefaultId}
                onLinked={async (id: number | null) => {
                  if (id != null) setFollowupConfigOpen(false);
                  updateFlags({
                    autoFollowup: id != null,
                    autoFollowupDefaultId: id,
                  });
                }}
              />
            </Box>
          )}
        </Paper>
      )}
      <Tabs
        value={tab}
        onChange={(_event, value) => setTab(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Filter builder" />
        <Tab label="GCN crossmatch" />
      </Tabs>
      <UnifiedBuilderProvider
        mode={showAnnotationBuilder ? "annotation" : "filter"}
      >
        <Box
          sx={{
            display: tab === 0 ? "block" : "none",
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            backgroundColor: "background.paper",
            maxHeight: { xs: "70vh", md: "80vh" },
            overflowY: "auto",
          }}
        >
          <Box
            sx={{
              ...builderSx,
              display: showAnnotationBuilder ? "block" : "none",
            }}
          >
            <AnnotationBuilderContent
              onBackToFilterBuilder={() => setShowAnnotationBuilder(false)}
            />
          </Box>
          <Box
            sx={{
              ...builderSx,
              display: showAnnotationBuilder ? "none" : "block",
            }}
          >
            <FilterBuilderContent
              onToggleAnnotationBuilder={() => setShowAnnotationBuilder(true)}
              filter={filter_v}
              setShowAnnotationBuilder={setShowAnnotationBuilder}
            />
          </Box>
        </Box>
      </UnifiedBuilderProvider>
      {tab === 1 && <GcnCrossmatchPlugin />}
    </Box>
  );
};

export default BoomFilterPlugins;
