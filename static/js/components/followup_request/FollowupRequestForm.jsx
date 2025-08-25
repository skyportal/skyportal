import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import "react-datepicker/dist/react-datepicker-cssmodules.css";

import CircularProgress from "@mui/material/CircularProgress";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import makeStyles from "@mui/styles/makeStyles";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import PropTypes from "prop-types";
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

import * as allocationActions from "../../ducks/allocations";
import * as instrumentsActions from "../../ducks/instruments";
import * as sourceActions from "../../ducks/source";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";
import {
  isSomeActiveRangeOrNoRange,
  rangeIsActive,
} from "../allocation/AllocationTable";

const useStyles = makeStyles(() => ({
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

const FollowupRequestForm = ({
  obj_id,
  instrumentList,
  instrumentFormParams,
  requestType,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations,
  );
  const allGroups = useSelector((state) => state.groups.all);
  const defaultAllocationId = useSelector(
    (state) => state.profile.preferences.followupDefault,
  );
  const [selectedAllocationId, setSelectedAllocationId] =
    useState(defaultAllocationId);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmationDialog, setShowConfirmationDialog] = useState(false);
  const [requestData, setRequestData] = useState(null);

  const [filteredAllocationList, setFilteredAllocationList] = useState([]);
  const [settingFilteredList, setSettingFilteredList] = useState(false);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update
      let data = [];
      if (
        !allocationListApiClassname ||
        allocationListApiClassname.length === 0
      ) {
        const result = await dispatch(
          allocationActions.fetchAllocationsApiClassname(),
        );
        data = result?.data || [];
      } else {
        data = allocationListApiClassname;
      }
      const tempAllocationLookUp = {};
      data?.forEach((allocation) => {
        tempAllocationLookUp[allocation.id] = allocation;
      });

      if (!selectedAllocationId) {
        if (data[0]?.default_share_group_ids?.length > 0) {
          setSelectedGroupIds(data[0]?.default_share_group_ids);
        } else {
          setSelectedGroupIds([data[0]?.group_id]);
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
    };

    getAllocations();

    if (
      !instrumentFormParams ||
      Object.keys(instrumentFormParams).length === 0
    ) {
      dispatch(instrumentsActions.fetchInstrumentForms());
    }
  }, [setSelectedAllocationId, setSelectedGroupIds, dispatch]);

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
          (allocation) =>
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
          (allocation) =>
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

  const groupLookUp = {};
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  allocationListApiClassname?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
    if (allocationLookUp[e.target.value]?.default_share_group_ids?.length > 0) {
      setSelectedGroupIds(
        allocationLookUp[e.target.value]?.default_share_group_ids,
      );
    } else {
      setSelectedGroupIds([allocationLookUp[e.target.value]?.group_id]);
    }
  };

  const submitFollowupRequest = async (formData) => {
    setIsSubmitting(true);
    const json = {
      obj_id,
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    await dispatch(sourceActions.submitFollowupRequest(json)).then(
      (response) => {
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

  const handleSubmit = async ({ formData }) => {
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

  const validate = (formData, errors) => {
    if (formData?.start_date && formData?.end_date) {
      if (formData.start_date > formData.end_date) {
        errors.start_date.addError("Start Date must come before End Date");
      }
    }
    if (
      !isSomeActiveRangeOrNoRange(
        allocationLookUp[selectedAllocationId].validity_ranges,
        new Date(formData.start_date || Date.now()),
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

  const schema =
    requestType === "forced_photometry"
      ? instrumentFormParams[
          allocationLookUp[selectedAllocationId].instrument_id
        ].formSchemaForcedPhotometry
      : instrumentFormParams[
          allocationLookUp[selectedAllocationId].instrument_id
        ].formSchema;

  if (schema && schema.properties?.start_date && schema.properties?.end_date) {
    if (requestType === "forced_photometry") {
      // edit the start and end date to be 30 days ending right now (in UTC)
      const endDate = new Date();
      const startDate = new Date(endDate - 30 * 24 * 60 * 60 * 1000);
      schema.properties.start_date.default = startDate
        .toISOString()
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
      schema.properties.end_date.default = endDate
        .toISOString()
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
    } else {
      // here, the range isn't necessarily 30 days, so we look at the values provided
      // calculate the range, and then update the default to be:
      // - start_date: now
      // - end_date: now + range
      const { start_date, end_date } = schema.properties;
      const startDate = new Date(start_date.default);
      const endDate = new Date(end_date.default);
      const range = endDate - startDate;

      let newStartDate = new Date();
      let newEndDate = new Date(newStartDate.getTime() + range);

      newStartDate = newStartDate.toISOString();
      newEndDate = newEndDate.toISOString();

      if (start_date.format === "date") {
        newStartDate = newStartDate.split("T")[0];
      }
      if (end_date.format === "date") {
        newEndDate = newEndDate.split("T")[0];
      }
      schema.properties.start_date.default = newStartDate
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
      schema.properties.end_date.default = newEndDate
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
    }
  }

  const { uiSchema } =
    instrumentFormParams[allocationLookUp[selectedAllocationId].instrument_id];

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
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
                  (range) => (
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
            schema={schema}
            validator={validator}
            uiSchema={uiSchema}
            customValidate={validate}
            onSubmit={handleSubmit}
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

FollowupRequestForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
  ).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any),
    uiSchema: PropTypes.objectOf(PropTypes.any),
    implementedMethods: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
  requestType: PropTypes.string,
};

FollowupRequestForm.defaultProps = {
  requestType: "triggered",
};

export default FollowupRequestForm;
