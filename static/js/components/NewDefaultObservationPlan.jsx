import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import GcnNoticeTypesSelect from "./GcnNoticeTypesSelect";
import GcnTagsSelect from "./GcnTagsSelect";
import LocalizationTagsSelect from "./LocalizationTagsSelect";

import * as defaultObservationPlansActions from "../ducks/default_observation_plans";
import * as allocationActions from "../ducks/allocations";
import * as instrumentsActions from "../ducks/instruments";
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

const NewDefaultObservationPlan = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState([]);
  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations
  );

  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [
    fetchingInstrumentObsplanFormParams,
    setFetchingInstrumentObsplanFormParams,
  ] = useState(false);

  const { instrumentList, instrumentObsplanFormParams } = useSelector(
    (state) => state.instruments
  );

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(
        allocationActions.fetchAllocationsApiObsplan()
      );

      const { data } = result;
      setSelectedAllocationId(data[0]?.id);
      setSelectedGroupIds([data[0]?.group_id]);
    };

    getAllocations();

    if (
      Object.keys(instrumentObsplanFormParams).length === 0 &&
      !fetchingInstrumentObsplanFormParams
    ) {
      setFetchingInstrumentObsplanFormParams(true);
      dispatch(instrumentsActions.fetchInstrumentObsplanForms()).then(() => {
        setFetchingInstrumentObsplanFormParams(false);
      });
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedAllocationId, setSelectedGroupIds]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiObsplan is not
  // empty.
  if (
    allocationListApiObsplan.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentObsplanFormParams).length === 0
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
  allocationListApiObsplan?.forEach((allocation) => {
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
    const { default_plan_name } = formData;
    delete formData.default_plan_name;
    const filters = {
      notice_types: selectedGcnNoticeTypes,
      gcn_tags: selectedGcnTags,
      localization_tags: selectedLocalizationTags,
    };
    const json = {
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
      filters,
      default_plan_name,
    };

    dispatch(
      defaultObservationPlansActions.submitDefaultObservationPlan(json)
    ).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification("Successfully created default observation plan")
        );
      }
    });
  };

  const { formSchema, uiSchema } =
    instrumentObsplanFormParams[
      allocationLookUp[selectedAllocationId].instrument_id
    ];
  formSchema.properties.default_plan_name = {
    default: "DEFAULT-PLAN-NAME",
    type: "string",
  };

  const keys_to_remove = ["start_date", "end_date", "queue_name"];
  keys_to_remove.forEach((key) => {
    if (Object.keys(formSchema.properties).includes(key)) {
      delete formSchema.properties[key];
    }
    if (formSchema.required.includes(key)) {
      formSchema.required.splice(formSchema.required.indexOf(key), 1);
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
        {allocationListApiObsplan?.map((allocation) => (
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
      <GcnNoticeTypesSelect
        selectedGcnNoticeTypes={selectedGcnNoticeTypes}
        setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
      />
      <GcnTagsSelect
        selectedGcnTags={selectedGcnTags}
        setSelectedGcnTags={setSelectedGcnTags}
      />
      <LocalizationTagsSelect
        selectedLocalizationTags={selectedLocalizationTags}
        setSelectedLocalizationTags={setSelectedLocalizationTags}
      />
      <div data-testid="observationplan-request-form">
        <div>
          <Form
            schema={formSchema}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit}
          />
        </div>
      </div>
    </div>
  );
};

export default NewDefaultObservationPlan;