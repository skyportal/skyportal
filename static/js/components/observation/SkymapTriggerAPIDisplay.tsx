import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";

import { makeStyles } from "tss-react/mui";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "../Button";

import FindGcnEvents from "../gcn/FindGcnEvents";

import { useAppSelector } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetApiSkymapTriggersQuery,
  usePostApiSkymapTriggerMutation,
  useDeleteApiSkymapTriggerMutation,
} from "../../ducks/skymap_triggers";
import { useGetAllocationsApiObsplanQuery } from "../../ducks/allocations";

dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  marginTop: {
    marginTop: "1rem",
  },
  select: {
    width: "100%",
    marginBottom: "1rem",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    marginTop: "1rem",
    width: "99%",
  },
  selectItems: {
    marginBottom: "1rem",
  },
}));

const SkymapTriggerAPIDisplay = () => {
  const { classes } = useStyles();

  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [triggerList, setTriggerList] = useState<string[]>(["None"]);
  const [selectedTriggerName, setSelectedTriggerName] = useState("None");

  const [selectedGcnEventId, setSelectedGcnEventId] = useState<any>(null);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);

  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery({
      apiImplements: "send_skymap",
    });
  const allGroups = useGetGroupsQuery().data?.all ?? null;

  const [postApiSkymapTrigger] = usePostApiSkymapTriggerMutation();
  const [deleteApiSkymapTrigger] = useDeleteApiSkymapTriggerMutation();

  const { data: skymapTriggers } = useGetApiSkymapTriggersQuery(
    { id: selectedAllocationId },
    {
      skip: !selectedAllocationId || !(allocationListApiObsplan?.length > 0),
    },
  );

  useEffect(() => {
    if (allocationListApiObsplan?.length > 0) {
      setSelectedAllocationId(allocationListApiObsplan[0]?.["id"]);
    }
  }, [allocationListApiObsplan]);

  useEffect(() => {
    if (skymapTriggers?.trigger_names?.length) {
      setTriggerList(skymapTriggers.trigger_names);
      setSelectedTriggerName(skymapTriggers.trigger_names[0] ?? "None");
    } else {
      setTriggerList(["None"]);
      setSelectedTriggerName("None");
    }
  }, [skymapTriggers]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return <h3>No telescopes/instruments available...</h3>;
  }

  if (allocationListApiObsplan.length === 0) {
    return <h3>No allocations with an observation plan API...</h3>;
  }

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const allocationLookUp: Record<string, any> = {};

  allocationListApiObsplan?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const handleAdd = async () => {
    try {
      await postApiSkymapTrigger({
        allocation_id: selectedAllocationId,
        localization_id: selectedLocalizationId,
      }).unwrap();
    } catch {
      // notification handled by baseQuery
    }
  };

  const handleDelete = async () => {
    try {
      await deleteApiSkymapTrigger({
        id: selectedAllocationId,
        params: { trigger_name: selectedTriggerName },
      }).unwrap();
    } catch {
      // notification handled by baseQuery
    }
  };

  const handleSelectedAllocationChange = async (e: any) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSelectedTriggerNameChange = async (e: any) => {
    setSelectedTriggerName(e.target.value);
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
        className={classes.select}
      >
        {allocationListApiObsplan?.map((allocation: any) => (
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
      <div className={classes.selectItems}>
        <FindGcnEvents
          selectedGcnEventId={selectedGcnEventId}
          setSelectedGcnEventId={setSelectedGcnEventId}
          selectedLocalizationId={selectedLocalizationId}
          setSelectedLocalizationId={setSelectedLocalizationId}
        />
      </div>
      <InputLabel id="triggerNameSelectLabel">Trigger Name</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="triggerNameSelectLabel"
        value={selectedTriggerName}
        onChange={handleSelectedTriggerNameChange}
        name="followupRequestAllocationSelect"
        className={classes.select}
      >
        {triggerList?.map((triggerName) => (
          <MenuItem
            value={triggerName}
            key={triggerName}
            className={classes.SelectItem}
          >
            {triggerName}
          </MenuItem>
        ))}
      </Select>
      <Button
        onClick={() => {
          handleAdd();
        }}
        data-testid="add-trigger-button"
      >
        Add trigger
      </Button>
      <Button
        onClick={() => {
          handleDelete();
        }}
        data-testid="delete-trigger-button"
      >
        Delete trigger
      </Button>
    </div>
  );
};

export default SkymapTriggerAPIDisplay;
