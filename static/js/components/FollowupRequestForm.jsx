import React, { useState, useEffect } from "react";
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
import * as sourceActions from "../ducks/source";
import * as allocationActions from "../ducks/allocations";
import * as instrumentActions from "../ducks/instruments";
import GroupShareSelect from "./GroupShareSelect";

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
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiClassname } = useSelector(
    (state) => state.allocations
  );
  const allGroups = useSelector((state) => state.groups.all);
  const defaultAllocationId = useSelector(
    (state) => state.profile.preferences.followupDefault
  );
  const [selectedAllocationId, setSelectedAllocationId] =
    useState(defaultAllocationId);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update
      const result = await dispatch(
        allocationActions.fetchAllocationsApiClassname()
      );

      const { data } = result;
      const tempAllocationLookUp = {};
      data?.forEach((allocation) => {
        tempAllocationLookUp[allocation.id] = allocation;
      });

      if (!selectedAllocationId) {
        setSelectedAllocationId(data[0]?.id);
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
          tempAllocationLookUp[selectedAllocationId]?.default_share_group_ids
        );
      } else {
        setSelectedGroupIds([
          tempAllocationLookUp[selectedAllocationId]?.group_id,
        ]);
      }
    };

    getAllocations();

    dispatch(
      instrumentActions.fetchInstrumentForms({
        apiType: "api_classname",
      })
    );
  }, [setSelectedAllocationId, setSelectedGroupIds, dispatch]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationList is not
  // empty.
  if (
    allocationListApiClassname.length === 0 ||
    !selectedAllocationId ||
    !selectedGroupIds ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No allocations with an observation plan API...</h3>;
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
        allocationLookUp[e.target.value]?.default_share_group_ids
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
    await dispatch(sourceActions.submitFollowupRequest(json));
    setIsSubmitting(false);
  };

  const validate = (formData, errors) => {
    if (
      formData.start_date &&
      formData.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    return errors;
  };

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationListApiClassname?.map((allocation) => (
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
      <div data-testid="followup-request-form">
        {allocationLookUp[selectedAllocationId].instrument_id in
        instrumentFormParams ? (
          <Form
            schema={
              instrumentFormParams[
                allocationLookUp[selectedAllocationId].instrument_id
              ].formSchema
            }
            validator={validator}
            uiSchema={
              instrumentFormParams[
                allocationLookUp[selectedAllocationId].instrument_id
              ].uiSchema
            }
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
    })
  ).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    implementedMethods: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }).isRequired,
};

export default FollowupRequestForm;
