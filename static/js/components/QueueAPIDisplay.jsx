import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import makeStyles from "@mui/styles/makeStyles";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "./Button";

import * as queuedObservationActions from "../ducks/queued_observations";
import * as allocationActions from "../ducks/allocations";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
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
}));

const QueueAPIDisplay = () => {
  const classes = useStyles();

  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const [queueList, setQueueList] = useState(["None"]);
  const [selectedQueueName, setSelectedQueueName] = useState("None");

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations,
  );
  const allGroups = useSelector((state) => state.groups.all);

  const dispatch = useDispatch();

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
    };

    getAllocations();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  useEffect(() => {
    const getQueues = async () => {
      if (selectedAllocationId && allocationListApiObsplan?.length > 0) {
        const response = await dispatch(
          queuedObservationActions.requestAPIQueues(selectedAllocationId),
        );
        if (response?.data?.queue_names?.length > 0) {
          setQueueList(response.data.queue_names);
          setSelectedQueueName(response.data.queue_names[0]);
        } else {
          setQueueList(["None"]);
          setSelectedQueueName("None");
        }
      }
    };
    getQueues();
  }, [selectedAllocationId]);

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

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allocationListApiObsplan?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const handleDelete = async () => {
    await dispatch(
      queuedObservationActions.deleteAPIQueue(selectedAllocationId, {
        queueName: selectedQueueName,
      }),
    );
  };

  const handleSelectedAllocationChange = async (e) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSelectedQueueNameChange = async (e) => {
    setSelectedQueueName(e.target.value);
  };

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        defaultValue={selectedAllocationId || ""}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.select}
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
      <InputLabel id="queueNameSelectLabel">Queue Name</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="queueNameSelectLabel"
        value={selectedQueueName}
        onChange={handleSelectedQueueNameChange}
        name="followupRequestAllocationSelect"
        className={classes.select}
      >
        {queueList?.map((queueName) => (
          <MenuItem
            value={queueName}
            key={queueName}
            className={classes.SelectItem}
          >
            {queueName}
          </MenuItem>
        ))}
      </Select>
      <Button
        onClick={() => {
          handleDelete();
        }}
        data-testid="delete-queue-button"
      >
        Delete queue
      </Button>
    </div>
  );
};

export default QueueAPIDisplay;
