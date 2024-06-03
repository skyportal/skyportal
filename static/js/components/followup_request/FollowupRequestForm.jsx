import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";

import * as sourceActions from "../../ducks/source";
import * as allocationActions from "../../ducks/allocations";
import * as instrumentsActions from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  allocationSelect: {
    width: "100%",
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
    if (
      filteredAllocationList.length === 0 &&
      allocationListApiClassname.length > 0 &&
      Object.keys(instrumentFormParams).length > 0 &&
      settingFilteredList === false
    ) {
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

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    const json = {
      obj_id,
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
    };
    const result = await dispatch(sourceActions.submitFollowupRequest(json));
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Photometry successfully requested."));
    }
  };

  const validate = (formData, errors) => {
    if (formData?.start_date && formData?.end_date) {
      if (formData.start_date > formData.end_date) {
        errors.start_date.addError("Start Date must come before End Date");
      }
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
      schema.properties.start_date.default = startDate // eslint-disable-line prefer-destructuring
        .toISOString()
        .replace("Z", "")
        .replace("T", " ")
        .split(".")[0];
      schema.properties.end_date.default = endDate // eslint-disable-line prefer-destructuring
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
      const newStartDate = new Date();
      const newEndDate = new Date(newStartDate.getTime() + range);
      schema.properties.start_date.default = newStartDate // eslint-disable-line prefer-destructuring
        .toISOString()
        .split("T")[0];
      schema.properties.end_date.default = newEndDate // eslint-disable-line prefer-destructuring
        .toISOString()
        .split("T")[0];
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
        {filteredAllocationList?.map((allocation) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={classes.allocationSelectItem}
          >
            {`${
              telLookUp[instLookUp[allocation.instrument_id]?.telescope_id]
                ?.name
            } / ${instLookUp[allocation.instrument_id]?.name} - ${
              groupLookUp[allocation.group_id]?.name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
      <br />
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
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
            liveValidate
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
    formSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    implementedMethods: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }).isRequired,
  requestType: PropTypes.string,
};

FollowupRequestForm.defaultProps = {
  requestType: "triggered",
};

export default FollowupRequestForm;
