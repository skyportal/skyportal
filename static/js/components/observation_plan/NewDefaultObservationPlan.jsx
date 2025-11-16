import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import Box from "@mui/material/Box";

import { showNotification } from "baselayer/components/Notifications";
import GcnNoticeTypesSelect from "../gcn/GcnNoticeTypesSelect";
import GcnTagsSelect from "../gcn/GcnTagsSelect";
import GcnPropertiesSelect from "../gcn/GcnPropertiesSelect";
import LocalizationTagsSelect from "../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../localization/LocalizationPropertiesSelect";
import PlanPropertiesSelect from "./PlanPropertiesSelect";

import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import * as allocationActions from "../../ducks/allocations";
import * as instrumentsActions from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

const conversions = {
  FAR: {
    backendUnit: "Hz",
    frontendUnit: "Per year",
    BackendToFrontend: (val) => parseFloat(val) * (365.25 * 24 * 60 * 60),
    FrontendToBackend: (val) => parseFloat(val) / (365.25 * 24 * 60 * 60),
  },
};

const comparators = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

const NewDefaultObservationPlan = ({ onClose }) => {
  const dispatch = useDispatch();
  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState([]);
  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState([]);
  const [selectedPlanProperties, setSelectedPlanProperties] = useState([]);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations,
  );
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [
    fetchingInstrumentObsplanFormParams,
    setFetchingInstrumentObsplanFormParams,
  ] = useState(false);

  const { instrumentList, instrumentObsplanFormParams } = useSelector(
    (state) => state.instruments,
  );

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(
        allocationActions.fetchAllocationsApiObsplan(),
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
    !allocationListApiObsplan.length ||
    !selectedAllocationId ||
    !Object.keys(instrumentObsplanFormParams).length
  ) {
    return <h3>No allocations with an observation plan API...</h3>;
  }

  if (!allGroups?.length || !telescopeList.length || !instrumentList.length) {
    return <CircularProgress color="secondary" />;
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
  allocationListApiObsplan?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }) => {
    const { default_plan_name, auto_send } = formData;
    delete formData.default_plan_name;
    delete formData.auto_send;
    const filters = {
      notice_types: selectedGcnNoticeTypes,
      gcn_tags: selectedGcnTags,
      localization_tags: selectedLocalizationTags,
      gcn_properties: selectedGcnProperties,
      localization_properties: selectedLocalizationProperties,
      plan_properties: selectedPlanProperties,
    };
    const json = {
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
      filters,
      default_plan_name,
      auto_send,
    };

    dispatch(
      defaultObservationPlansActions.submitDefaultObservationPlan(json),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification("Successfully created default observation plan"),
        );
        if (typeof onClose === "function") {
          onClose();
        }
      }
    });
  };

  const { formSchema, uiSchema } =
    instrumentObsplanFormParams[
      allocationLookUp[selectedAllocationId].instrument_id
    ];

  // make a copy
  const formSchemaCopy = JSON.parse(JSON.stringify(formSchema));
  formSchemaCopy.properties.default_plan_name = {
    default: "DEFAULT-PLAN-NAME",
    type: "string",
  };
  formSchemaCopy.properties.auto_send = {
    title: "Automatically send to telescope queue?",
    default: false,
    type: "boolean",
  };

  const keys_to_remove = ["start_date", "end_date", "queue_name"];
  keys_to_remove.forEach((key) => {
    if (Object.keys(formSchemaCopy.properties).includes(key)) {
      delete formSchemaCopy.properties[key];
    }
    if (formSchemaCopy.required.includes(key)) {
      formSchemaCopy.required.splice(formSchemaCopy.required.indexOf(key), 1);
    }
  });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <FormControl fullWidth>
        <InputLabel>Allocation</InputLabel>
        <Select
          label="Allocation"
          value={selectedAllocationId}
          onChange={(e) => setSelectedAllocationId(e.target.value)}
          name="followupRequestAllocationSelect"
        >
          {allocationListApiObsplan?.map((allocation) => (
            <MenuItem value={allocation.id} key={allocation.id}>
              {`${
                telLookUp[instLookUp[allocation.instrument_id].telescope_id]
                  .name
              } / ${instLookUp[allocation.instrument_id].name} - ${
                groupLookUp[allocation.group_id].name
              } (PI ${allocation.pi})`}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <div>
        <GroupShareSelect
          groupList={allGroups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
      </div>
      <Typography variant="h6">Event Filtering</Typography>
      <Box sx={{ display: "flex", gap: "0.2rem" }}>
        <GcnNoticeTypesSelect
          selectedGcnNoticeTypes={selectedGcnNoticeTypes}
          setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
        />
        <GcnTagsSelect
          selectedGcnTags={selectedGcnTags}
          setSelectedGcnTags={setSelectedGcnTags}
        />
      </Box>
      <GcnPropertiesSelect
        selectedGcnProperties={selectedGcnProperties}
        setSelectedGcnProperties={setSelectedGcnProperties}
        conversions={conversions}
        comparators={comparators}
      />
      <Divider />
      <Typography variant="h6">Localization Filtering</Typography>
      <LocalizationTagsSelect
        selectedLocalizationTags={selectedLocalizationTags}
        setSelectedLocalizationTags={setSelectedLocalizationTags}
      />
      <LocalizationPropertiesSelect
        selectedLocalizationProperties={selectedLocalizationProperties}
        setSelectedLocalizationProperties={setSelectedLocalizationProperties}
        comparators={comparators}
      />
      <Divider />
      <Typography variant="h6">Observation Plan Stats Filtering</Typography>
      <PlanPropertiesSelect
        selectedPlanProperties={selectedPlanProperties}
        setSelectedPlanProperties={setSelectedPlanProperties}
        comparators={comparators}
      />
      <Divider />
      <Typography variant="h6">Observation Plan Parameters</Typography>
      <Form
        data-testid="observationplan-request-form"
        schema={formSchemaCopy}
        validator={validator}
        uiSchema={uiSchema}
        onSubmit={handleSubmit}
      />
    </Box>
  );
};

NewDefaultObservationPlan.propTypes = {
  onClose: PropTypes.func,
};

NewDefaultObservationPlan.defaultProps = {
  onClose: null,
};

export default NewDefaultObservationPlan;
