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
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import GcnNoticeTypesSelect from "../gcn/GcnNoticeTypesSelect";
import GcnTagsSelect from "../gcn/GcnTagsSelect";
import GcnPropertiesSelect from "../gcn/GcnPropertiesSelect";
import LocalizationTagsSelect from "../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../localization/LocalizationPropertiesSelect";

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

const useStyles = makeStyles((theme) => ({
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
  form_group: {
    display: "flex",
    flexDirection: "column",
    alignItems: "left",
    gap: "0.5rem",
    width: "100%",
    marginTop: "0.5rem",
    marginBottom: "0.5rem",
  },
  form_group_title: {
    fontSize: "1.2rem",
  },
  form_subgroup: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "0.25rem",
    width: "100%",
    "& > div": {
      width: "100%",
    },
  },
  formGroupDivider: {
    width: "100%",
    height: "2px",
    background: theme.palette.grey[600],
    margin: "0.5rem 0",
  },
  formSubGroupDivider: {
    width: "100%",
    height: "2px",
    background: theme.palette.grey[300],
    margin: "0.5rem 0",
  },
}));

const NewDefaultObservationPlan = ({ onClose }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState([]);
  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState([]);

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

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

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
      <div className={classes.formGroupDivider} />
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div className={classes.formGroupDivider} />
      <div className={classes.form_group}>
        <Typography className={classes.form_group_title}>
          Event Filtering
        </Typography>
        <div className={classes.form_subgroup}>
          <GcnNoticeTypesSelect
            selectedGcnNoticeTypes={selectedGcnNoticeTypes}
            setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
          />
          <GcnTagsSelect
            selectedGcnTags={selectedGcnTags}
            setSelectedGcnTags={setSelectedGcnTags}
          />
        </div>
        <div className={classes.formSubGroupDivider} />
        <div className={classes.form_subgroup}>
          <GcnPropertiesSelect
            selectedGcnProperties={selectedGcnProperties}
            setSelectedGcnProperties={setSelectedGcnProperties}
            conversions={conversions}
            comparators={comparators}
          />
        </div>
      </div>
      <div className={classes.formGroupDivider} />
      <div className={classes.form_group}>
        <Typography className={classes.form_group_title}>
          Localization Filtering
        </Typography>
        <div className={classes.form_subgroup}>
          <LocalizationTagsSelect
            selectedLocalizationTags={selectedLocalizationTags}
            setSelectedLocalizationTags={setSelectedLocalizationTags}
          />
        </div>
        <div className={classes.formSubGroupDivider} />
        <div className={classes.form_subgroup}>
          <LocalizationPropertiesSelect
            selectedLocalizationProperties={selectedLocalizationProperties}
            setSelectedLocalizationProperties={
              setSelectedLocalizationProperties
            }
          />
        </div>
      </div>
      <div className={classes.formGroupDivider} />
      <div data-testid="observationplan-request-form">
        <Typography className={classes.form_group_title}>
          Observation Plan Parameters
        </Typography>
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

NewDefaultObservationPlan.propTypes = {
  onClose: PropTypes.func,
};

NewDefaultObservationPlan.defaultProps = {
  onClose: null,
};

export default NewDefaultObservationPlan;
