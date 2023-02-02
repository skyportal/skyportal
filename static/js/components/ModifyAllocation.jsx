import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "./GroupShareSelect";
import { modifyAllocation } from "../ducks/allocation";
import { fetchAllocations } from "../ducks/allocations";
import * as groupActions from "../ducks/group";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  groupSelect: {
    width: "20rem",
    marginBottom: "0.75rem",
  },
  usersSelect: {
    width: "20rem",
    marginBottom: "0.75rem",
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const ModifyAllocation = () => {
  const [selectedAllocationId, setSelectedAllocationId] = useState(null);
  const { allocationList } = useSelector((state) => state.allocations);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const allGroups = useSelector((state) => state.groups.all);
  const groups = useSelector((state) => state.groups.userAccessible);
  const group = useSelector((state) => state.group);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const dispatch = useDispatch();
  const classes = useStyles();

  const {
    control,
    getValues,

    formState: { errors },
  } = useForm();

  useEffect(() => {
    if (selectedGroup) {
      dispatch(groupActions.fetchGroup(selectedGroup.id));
    }
  }, [selectedGroup, dispatch]);

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(fetchAllocations());

      const { data } = result;
      setSelectedAllocationId(data[0]?.id);
    };

    getAllocations();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedAllocationId]);

  if (
    allocationList.length === 0 ||
    instrumentList.length === 0 ||
    telescopeList.length === 0
  ) {
    return <h3>No allocations available...</h3>;
  }

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if instruments is not
  // empty.
  if (!selectedAllocationId) {
    return <h3>No allocations available...</h3>;
  }

  const validateGroup = () => {
    const formState = getValues();
    return formState.group.length === 1;
  };

  const validateUsers = () => {
    const formState = getValues();
    return formState.users.length >= 0;
  };

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((thisGroup) => {
    groupLookUp[thisGroup.id] = thisGroup;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allocationList?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(365, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }) => {
    const formState = getValues();
    formData.group_id = formState.group.id;
    formData.allocation_admin_ids = [];
    formState.users.forEach((user) => {
      formData.allocation_admin_ids.push(user.id);
    });
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    if (selectedGroupIds.length > 0) {
      formData.default_share_group_ids = selectedGroupIds;
    }
    formData.instrument_id =
      allocationLookUp[selectedAllocationId].instrument_id;
    const result = await dispatch(
      modifyAllocation(selectedAllocationId, formData)
    );
    if (result.status === "success") {
      dispatch(showNotification("Allocation saved"));
      dispatch(fetchAllocations());
    }
  };

  const userLabel = (user) => {
    let label = user.username;
    if (user.first_name && user.last_name) {
      label = `${user.first_name} ${user.last_name} (${user.username})`;
      if (user.affiliations && user.affiliations.length > 0) {
        label = `${label} (${user.affiliations.join()})`;
      }
    }
    return label;
  };

  const handleSelectedAllocationChange = (e) => {
    setSelectedAllocationId(e.target.value);
  };

  function validate(formData, validationErrors) {
    if (nowDate > formData.end_date) {
      validationErrors.end_date.addError(
        "End date must be after current time, please fix."
      );
    }
    if (formData.start_date > formData.end_date) {
      validationErrors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    return validationErrors;
  }

  const allocationFormSchema = {
    type: "object",
    properties: {
      pi: {
        type: "string",
        title: "PI",
      },
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date (Local Time)",
        default: defaultStartDate,
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date (Local Time)",
        default: defaultEndDate,
      },
      hours_allocated: {
        type: "number",
        title: "Hours allocated",
      },
      _altdata: {
        type: "string",
        title: "Alternative json data (i.e. {'slack_token': 'testtoken'}",
      },
    },
    required: ["pi", "start_date", "end_date", "hours_allocated"],
  };

  return (
    <div>
      <InputLabel id="instrumentSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="modifyAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationList?.map((allocation) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={classes.allocationSelectItem}
          >
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id]?.name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
      <Controller
        name="group"
        render={({ field: { onChange, value } }) => (
          <Autocomplete
            id="addGroup"
            onChange={(e, data) => {
              setSelectedGroup(data);
              onChange(data);
            }}
            value={value}
            options={groups}
            getOptionLabel={(thisGroup) => thisGroup.name}
            filterSelectedOptions
            data-testid="addGroup"
            renderInput={(field) => (
              <TextField
                // eslint-disable-next-line react/jsx-props-no-spreading
                {...field}
                error={!!errors.group}
                variant="outlined"
                label="Select Group"
                size="small"
                className={classes.groupSelect}
                data-testid="addGroupTextField"
              />
            )}
          />
        )}
        control={control}
        rules={{ validate: validateGroup }}
      />
      <div>
        {group?.users && (
          <>
            <Controller
              name="users"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  id="addUsersFromGroupSelect"
                  onChange={(e, data) => {
                    onChange(data);
                  }}
                  value={value}
                  options={group?.users}
                  getOptionLabel={(user) => userLabel(user)}
                  filterSelectedOptions
                  data-testid="addUsersFromGroupSelect"
                  renderInput={(field) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...field}
                      error={!!errors.users}
                      variant="outlined"
                      label="Select Allocation Admins"
                      size="small"
                      className={classes.userSelect}
                      data-testid="addUsersFromGroupTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateUsers }}
            />
          </>
        )}
      </div>
      <Form
        schema={allocationFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        // eslint-disable-next-line react/jsx-no-bind
        validate={validate}
        liveValidate
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </div>
  );
};

export default ModifyAllocation;
