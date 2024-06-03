import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";

import * as defaultFollowupRequestsActions from "../ducks/default_followup_requests";
import * as allocationActions from "../ducks/allocations";
import * as instrumentsActions from "../ducks/instruments";
import GroupShareSelect from "./group/GroupShareSelect";

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
  Select: {
    width: "100%",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const NewDefaultFollowupRequest = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations,
  );

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      if (
        !allocationListApiClassname ||
        allocationListApiClassname.length === 0
      ) {
        await dispatch(allocationActions.fetchAllocationsApiClassname());
      }
    };

    getAllocations();

    if (
      !instrumentFormParams ||
      Object.keys(instrumentFormParams).length === 0
    ) {
      dispatch(instrumentsActions.fetchInstrumentForms());
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  const filteredAllocationListApiClassname = allocationListApiClassname.filter(
    (allocation) =>
      allocation.instrument_id in instrumentFormParams &&
      instrumentFormParams[allocation.instrument_id].formSchema !== null &&
      instrumentFormParams[allocation.instrument_id].formSchema !== undefined &&
      allocation.types.includes("triggered"),
  );

  useEffect(() => {
    if (!selectedAllocationId) {
      setSelectedAllocationId(filteredAllocationListApiClassname[0]?.id);
      setSelectedGroupIds([filteredAllocationListApiClassname[0]?.group_id]);
    }
  }, [allocationListApiClassname, instrumentFormParams, dispatch]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiClassname is not
  // empty.
  if (
    filteredAllocationListApiClassname.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No allocations with an API class...</h3>;
  }

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  filteredAllocationListApiClassname?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSubmit = async ({ formData }) => {
    const { default_followup_name, source_filter } = formData;
    delete formData.default_followup_name;
    delete formData.source_filter;
    const json = {
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
      default_followup_name,
      source_filter,
    };
    await dispatch(
      defaultFollowupRequestsActions.submitDefaultFollowupRequest(json),
    );
  };

  const instrumentFormParam =
    instrumentFormParams[allocationLookUp[selectedAllocationId].instrument_id];
  if (!instrumentFormParam) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const { formSchema, uiSchema } = instrumentFormParam;

  // make a copy for both
  const formSchemaCopy = JSON.parse(JSON.stringify(formSchema));

  formSchemaCopy.properties.default_followup_name = {
    default: "DEFAULT-PLAN-NAME",
    type: "string",
  };
  formSchemaCopy.properties.source_filter = {
    title: "Source filter data (i.e. {'classification': 'microlensing'})",
    type: "string",
  };

  const keys_to_remove = ["start_date", "end_date", "queue_name"];
  keys_to_remove.forEach((key) => {
    if (Object.keys(formSchemaCopy.properties).includes(key)) {
      delete formSchemaCopy.properties[key];
    }
    if (
      formSchemaCopy.required?.length > 0 &&
      formSchemaCopy.required.includes(key)
    ) {
      formSchemaCopy.required.splice(formSchemaCopy.required.indexOf(key), 1);
    }
  });

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.Select}
      >
        {filteredAllocationListApiClassname?.map((allocation) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={classes.SelectItem}
          >
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id].name
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
      <div data-testid="followup-request-form">
        <div>
          <Form
            schema={formSchemaCopy}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit}
          />
        </div>
      </div>
    </div>
  );
};

export default NewDefaultFollowupRequest;
