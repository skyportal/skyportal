import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import { makeStyles } from "tss-react/mui";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import Chip from "@mui/material/Chip";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import * as instrumentsActions from "../../ducks/instruments";
import * as sourceActions from "../../ducks/source";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";
import {
  isSomeActiveRangeOrNoRange,
  rangeIsActive,
} from "../allocation/AllocationTable";

const useStyles = makeStyles()(() => ({
  marginTop: {
    marginTop: "1rem",
  },
  allocationSelect: {
    width: "100%",
    marginBottom: "1rem",
  },
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

interface FollowupRequestFormProps {
  obj_id: string;
  instrumentList: any[];
  instrumentFormParams: Record<string, any>;
  requestType?: string;
}

const FollowupRequestForm = ({
  obj_id,
  instrumentList,
  instrumentFormParams,
  requestType = "triggered",
}: FollowupRequestFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const defaultAllocationId = useAppSelector(
    (state) => (state.profile.preferences as any).followupDefault,
  );
  const [selectedAllocationId, setSelectedAllocationId] =
    useState(defaultAllocationId);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmationDialog, setShowConfirmationDialog] = useState(false);
  const [requestData, setRequestData] = useState<any>(null);

  const [filteredAllocationList, setFilteredAllocationList] = useState<any[]>(
    [],
  );
  const [settingFilteredList, setSettingFilteredList] = useState(false);

  useEffect(() => {
    const data = allocationListApiClassname || [];
    if (data.length === 0) {
      return;
    }
    const tempAllocationLookUp: any = {};
    data.forEach((allocation: any) => {
      tempAllocationLookUp[allocation.id] = allocation;
    });

    if (!selectedAllocationId) {
      if (data[0]?.["default_share_group_ids"]?.length > 0) {
        setSelectedGroupIds(data[0]?.["default_share_group_ids"]);
      } else {
        setSelectedGroupIds([data[0]?.["group_id"]]);
      }
    } else if (
      tempAllocationLookUp[selectedAllocationId]?.default_share_group_ids
        ?.length > 0
    ) {
      setSelectedGroupIds(
        tempAllocationLookUp[selectedAllocationId]?.default_share_group_ids,
      );
    } else {
      setSelectedGroupIds([
        tempAllocationLookUp[selectedAllocationId]?.group_id,
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    allocationListApiClassname,
    setSelectedAllocationId,
    setSelectedGroupIds,
  ]);

  useEffect(() => {
    if (
      !instrumentFormParams ||
      Object.keys(instrumentFormParams).length === 0
    ) {
      dispatch(instrumentsActions.fetchInstrumentForms());
    }
  }, [dispatch, instrumentFormParams]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationList is not
  // empty.

  // only keep allocations in allocationListApiClassname where there is a corresponding
  // instrument form params with a non null formSchema
  useEffect(() => {
    async function filterAllocations() {
      setSettingFilteredList(true);
      if (requestType === "triggered") {
        const filtered = (allocationListApiClassname || []).filter(
          (allocation: any) =>
            allocation.instrument_id in instrumentFormParams &&
            instrumentFormParams[allocation.instrument_id].formSchema !==
              null &&
            instrumentFormParams[allocation.instrument_id].formSchema !==
              undefined &&
            allocation.types.includes("triggered"),
        );
        setFilteredAllocationList(filtered);
      } else if (requestType === "forced_photometry") {
        const filtered = (allocationListApiClassname || []).filter(
          (allocation: any) =>
            allocation.instrument_id in instrumentFormParams &&
            instrumentFormParams[allocation.instrument_id]
              .formSchemaForcedPhotometry !== null &&
            instrumentFormParams[allocation.instrument_id]
              .formSchemaForcedPhotometry !== undefined &&
            allocation.types.includes("forced_photometry"),
        );
        setFilteredAllocationList(filtered);
      }
      setSettingFilteredList(false);
    }
    if (settingFilteredList === false) {
      filterAllocations();
    }
  }, [allocationListApiClassname, instrumentFormParams, settingFilteredList]);

  useEffect(() => {
    if (
      filteredAllocationList?.length > 0 &&
      (!selectedAllocationId ||
        !filteredAllocationList.some(
          (allocation) => allocation.id === selectedAllocationId,
        ))
    ) {
      setSelectedAllocationId(filteredAllocationList[0]?.id);
    }
  }, [filteredAllocationList]);

  if (
    filteredAllocationList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return (
      <h3>
        {`No allocations with an API class ${
          requestType === "forced_photometry" ? "(for forced photometry) " : ""
        }where found..`}
        .
      </h3>
    );
  }

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0 ||
    !filteredAllocationList.some(
      (allocation) => allocation.id === selectedAllocationId,
    )
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const groupLookUp: any = {};
  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: any = {};
  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp: any = {};
  allocationListApiClassname?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: any = {};
  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedAllocationChange = (e: any) => {
    setSelectedAllocationId(e.target.value);
    if (allocationLookUp[e.target.value]?.default_share_group_ids?.length > 0) {
      setSelectedGroupIds(
        allocationLookUp[e.target.value]?.default_share_group_ids,
      );
    } else {
      setSelectedGroupIds([allocationLookUp[e.target.value]?.group_id]);
    }
  };

  const submitFollowupRequest = async (formData: any) => {
    setIsSubmitting(true);
    const json = {
      obj_id,
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    await dispatch(sourceActions.submitFollowupRequest(json)).then(
      (response: any) => {
        setIsSubmitting(false);
        if (response.status === "success") {
          if (response.data.request_status?.startsWith("rejected")) {
            dispatch(showNotification("Request has been rejected.", "warning"));
          } else {
            dispatch(showNotification("Request successfully submitted."));
          }
        }
      },
    );
    setIsSubmitting(false);
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    // if the method does not implement a delete, show a confirmation dialog
    let allocation = allocationLookUp[selectedAllocationId];
    let instrument_id = allocation.instrument_id;
    const implementsDelete =
      instrumentFormParams[instrument_id].methodsImplemented.delete;
    if (!implementsDelete) {
      setRequestData(formData);
      setShowConfirmationDialog(true);
      return;
    }

    submitFollowupRequest(formData);
  };

  const validate = (formData: any, errors: any) => {
    if (formData?.start_date && formData?.end_date) {
      if (formData.start_date > formData.end_date) {
        errors.start_date.addError("Start Date must come before End Date");
      }
    }
    const startDateForRangeCheck = formData.start_date
      ? new Date(formData.start_date)
      : new Date();
    if (
      !isSomeActiveRangeOrNoRange(
        allocationLookUp[selectedAllocationId].validity_ranges,
        startDateForRangeCheck,
      )
    ) {
      if (formData.start_date) {
        errors.start_date.addError(
          "Start Date must be within an active allocation range",
        );
      } else {
        errors.__errors.push(
          "Current date must be within an active allocation range",
        );
      }
    }
    if (
      formData.end_date &&
      !isSomeActiveRangeOrNoRange(
        allocationLookUp[selectedAllocationId].validity_ranges,
        new Date(formData.end_date),
      )
    ) {
      errors.end_date.addError(
        "End Date must be within an active allocation range",
      );
    }

    return errors;
  };

  const baseSchema =
    requestType === "forced_photometry"
      ? instrumentFormParams[
          allocationLookUp[selectedAllocationId].instrument_id
        ].formSchemaForcedPhotometry
      : instrumentFormParams[
          allocationLookUp[selectedAllocationId].instrument_id
        ].formSchema;

  let schema = baseSchema;
  if (
    baseSchema &&
    baseSchema.properties?.start_date &&
    baseSchema.properties?.end_date
  ) {
    let startDefault;
    let endDefault;
    if (requestType === "forced_photometry") {
      // edit the start and end date to be 30 days ending right now (in UTC)
      const endDate = new Date();
      const startDate = new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000);
      startDefault = startDate
        .toISOString()
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
      endDefault = endDate
        .toISOString()
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
    } else {
      // here, the range isn't necessarily 30 days, so we look at the values provided
      // calculate the range, and then update the default to be:
      // - start_date: now
      // - end_date: now + range
      const { start_date, end_date } = baseSchema.properties;
      const startDate = new Date(start_date.default);
      const endDate = new Date(end_date.default);
      const range = endDate.getTime() - startDate.getTime();

      let newStartDate: any = new Date();
      let newEndDate: any = new Date(newStartDate.getTime() + range);

      newStartDate = newStartDate.toISOString();
      newEndDate = newEndDate.toISOString();

      if (start_date.format === "date") {
        newStartDate = newStartDate.split("T")[0];
      }
      if (end_date.format === "date") {
        newEndDate = newEndDate.split("T")[0];
      }
      startDefault = newStartDate
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
      endDefault = newEndDate.replace("Z", "").replace("T", " ").split(".")[0];
    }
    schema = {
      ...baseSchema,
      properties: {
        ...baseSchema.properties,
        start_date: {
          ...baseSchema.properties.start_date,
          default: startDefault,
        },
        end_date: {
          ...baseSchema.properties.end_date,
          default: endDefault,
        },
      },
    };
  }

  const { uiSchema } =
    instrumentFormParams[allocationLookUp[selectedAllocationId].instrument_id];

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId as any}
        onChange={handleSelectedAllocationChange}
        name={
          requestType === "forced_photometry"
            ? "forcedPhotometryAllocationSelect"
            : "followupRequestAllocationSelect"
        }
        className={classes.allocationSelect}
      >
        {filteredAllocationList?.map((allocation) => {
          const label = `${
            telLookUp[instLookUp[allocation.instrument_id]?.telescope_id]?.name
          } / ${instLookUp[allocation.instrument_id]?.name} - ${
            groupLookUp[allocation.group_id]?.name
          } (PI ${allocation.pi})`;
          return (
            <MenuItem
              value={allocation.id}
              key={allocation.id}
              className={classes.allocationSelectItem}
            >
              {label}
              {!isSomeActiveRangeOrNoRange(allocation.validity_ranges) && (
                <Tooltip
                  title="This allocation is currently inactive. You can still submit requests for valid future dates."
                  arrow
                >
                  <Typography
                    component="span"
                    style={{ fontStyle: "italic", color: "grey" }}
                  >
                    {" (inactive)"}
                  </Typography>
                </Tooltip>
              )}
            </MenuItem>
          );
        })}
      </Select>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <GroupShareSelect
          groupList={allGroups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
        <Tooltip
          componentsProps={{ tooltip: { sx: { maxWidth: 340 } } }}
          title={
            allocationLookUp[selectedAllocationId]?.validity_ranges?.length
              ? allocationLookUp[selectedAllocationId]?.validity_ranges?.map(
                  (range: any) => (
                    <Typography
                      key={range.start_date}
                      variant="body1"
                      color={rangeIsActive(range) ? "lightgreen" : "default"}
                    >
                      {new Date(range.start_date)
                        .toISOString()
                        .replace("T", " ")
                        .slice(0, 19)}
                      {" - "}
                      {new Date(range.end_date)
                        .toISOString()
                        .replace("T", " ")
                        .slice(0, 19)}
                    </Typography>
                  ),
                )
              : "No validity ranges defined for this allocation."
          }
        >
          <Chip
            label="Validity Ranges"
            size="small"
            icon={<HelpOutlineIcon />}
          />
        </Tooltip>
      </Box>
      <div
        data-testid={
          requestType === "forced_photometry"
            ? "forced-photometry-form"
            : "followup-request-form"
        }
      >
        {allocationLookUp[selectedAllocationId] !== undefined &&
        allocationLookUp[selectedAllocationId]?.instrument_id in
          instrumentFormParams ? (
          <Form
            schema={schema as any}
            validator={validator}
            uiSchema={uiSchema}
            customValidate={validate}
            onSubmit={handleSubmit as any}
            disabled={isSubmitting}
          />
        ) : (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
        <Dialog
          open={showConfirmationDialog}
          onClose={() => setShowConfirmationDialog(false)}
          aria-labelledby="alert-dialog-title"
          aria-describedby="alert-dialog-description"
          maxWidth="sm"
        >
          <DialogTitle id="alert-dialog-title">
            {`Are you sure you want to submit this request?`}
          </DialogTitle>
          <DialogContent>
            {`This instrument's API does not implement a delete method, so you
            will not be able to delete this request once it is submitted.`}
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                submitFollowupRequest(requestData);
                setShowConfirmationDialog(false);
                setRequestData(null);
              }}
            >
              Confirm
            </Button>
            <Button
              onClick={() => {
                setShowConfirmationDialog(false);
                setRequestData(null);
              }}
            >
              Cancel
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default FollowupRequestForm;
