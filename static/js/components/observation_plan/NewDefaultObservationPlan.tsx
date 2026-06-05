import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
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

import { useSubmitDefaultObservationPlanMutation } from "../../ducks/default_observation_plans";
import { useGetAllocationsApiObsplanQuery } from "../../ducks/allocations";
import * as instrumentsActions from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";

const conversions: Record<string, any> = {
  FAR: {
    backendUnit: "Hz",
    frontendUnit: "Per year",
    BackendToFrontend: (val: any) => parseFloat(val) * (365.25 * 24 * 60 * 60),
    FrontendToBackend: (val: any) => parseFloat(val) / (365.25 * 24 * 60 * 60),
  },
};

const comparators: Record<string, string> = {
  lt: "<",
  le: "<=",
  eq: "=",
  ne: "!=",
  ge: ">",
  gt: ">=",
};

interface NewDefaultObservationPlanProps {
  onClose?: (() => void) | null;
}

const NewDefaultObservationPlan = ({
  onClose = null,
}: NewDefaultObservationPlanProps) => {
  const dispatch = useAppDispatch();
  const [submitDefaultObservationPlan] =
    useSubmitDefaultObservationPlanMutation();
  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState<any[]>(
    [],
  );
  const [selectedGcnTags, setSelectedGcnTags] = useState<any[]>([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState<any[]>([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState<
    any[]
  >([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState<any[]>([]);
  const [selectedPlanProperties, setSelectedPlanProperties] = useState<any[]>(
    [],
  );
  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery();
  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [
    fetchingInstrumentObsplanFormParams,
    setFetchingInstrumentObsplanFormParams,
  ] = useState(false);

  const { instrumentList, instrumentObsplanFormParams } = useAppSelector(
    (state) => state["instruments"],
  );

  useEffect(() => {
    if (allocationListApiObsplan?.length > 0 && !selectedAllocationId) {
      setSelectedAllocationId(allocationListApiObsplan[0]?.["id"]);
      setSelectedGroupIds([allocationListApiObsplan[0]?.["group_id"]]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allocationListApiObsplan]);

  useEffect(() => {
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
  }, [dispatch]);

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

  const groupLookUp: Record<string, any> = {};
  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};
  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp: Record<string, any> = {};
  allocationListApiObsplan?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: Record<string, any> = {};
  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }: { formData: any }) => {
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

    try {
      await submitDefaultObservationPlan(json).unwrap();
      dispatch(
        showNotification("Successfully created default observation plan"),
      );
      if (typeof onClose === "function") {
        onClose();
      }
    } catch {
      // error notification handled by the baseQuery
    }
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
          {allocationListApiObsplan?.map((allocation: any) => (
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
        schema={formSchemaCopy as any}
        validator={validator}
        uiSchema={uiSchema}
        onSubmit={handleSubmit as any}
      />
    </Box>
  );
};

export default NewDefaultObservationPlan;
