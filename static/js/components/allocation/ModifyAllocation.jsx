import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { modifyAllocation } from "../../ducks/allocation";
import { fetchAllocations } from "../../ducks/allocations";
import * as groupActions from "../../ducks/group";
import GroupShareSelect from "../group/GroupShareSelect";

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

const ModifyAllocation = ({ allocation_id, onClose }) => {
  const { allocationList } = useSelector((state) => state.allocations);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const allowedAllocationTypes = useSelector(
    (state) => state.config.allowedAllocationTypes,
  );
  const allGroups = useSelector((state) => state.groups.all);
  const groups = useSelector((state) => state.groups.userAccessible);
  const group = useSelector((state) => state.group);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [defaultStartDate, setDefaultStartDate] = useState(
    dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ"),
  );
  const [defaultEndDate, setDefaultEndDate] = useState(
    dayjs().add(365, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ"),
  );
  const dispatch = useDispatch();
  const classes = useStyles();

  const {
    control,
    formState: { errors },
  } = useForm();

  useEffect(() => {
    if (selectedGroup) {
      dispatch(groupActions.fetchGroup(selectedGroup.id));
    }
  }, [selectedGroup, dispatch]);

  useEffect(() => {
    const selectedAllocation = allocationList.find(
      (allocation) => allocation?.id === allocation_id,
    );
    if (selectedAllocation) {
      const currentGroup =
        groups.find((g) => g.id === selectedAllocation.group_id) || null;

      setSelectedGroup(currentGroup);
      setSelectedGroupIds(selectedAllocation.default_share_group_ids || []);

      setDefaultStartDate(
        dayjs(`${selectedAllocation.start_date}Z`)
          .utc()
          .format("YYYY-MM-DDTHH:mm:ssZ"),
      );
      setDefaultEndDate(
        dayjs(`${selectedAllocation.end_date}Z`)
          .utc()
          .format("YYYY-MM-DDTHH:mm:ssZ"),
      );
    }
  }, [allocation_id, allocationList]);

  useEffect(() => {
    if (group?.users && allocation_id) {
      const selectedAllocation = allocationList.find(
        (allocation) => allocation?.id === allocation_id,
      );
      setSelectedUsers(
        group.users.filter((user) =>
          selectedAllocation.allocation_users.some(
            (allocationUser) => allocationUser.id === user.id,
          ),
        ),
      );
    }
  }, [group]);

  if (
    allocationList.length === 0 ||
    instrumentList.length === 0 ||
    telescopeList.length === 0
  ) {
    return <h3>No allocations available...</h3>;
  }

  const validateGroup = () => selectedGroup !== null;

  const validateUsers = () => selectedUsers.length > 0;

  const groupLookUp = {};

  allGroups?.forEach((thisGroup) => {
    groupLookUp[thisGroup.id] = thisGroup;
  });

  const telLookUp = {};

  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp = {};

  allocationList?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};

  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }) => {
    formData.group_id = selectedGroup.id;
    formData.allocation_admin_ids = [];
    selectedUsers.forEach((user) => {
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
    formData.instrument_id = allocationLookUp[allocation_id].instrument_id;
    const result = await dispatch(modifyAllocation(allocation_id, formData));
    if (result.status === "success") {
      dispatch(showNotification("Allocation modified successfully"));
      if (typeof onClose === "function") {
        onClose();
      }
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

  function validate(formData, validationErrors) {
    if (nowDate > formData.end_date) {
      validationErrors.end_date.addError(
        "End date must be after current time, please fix.",
      );
    }
    if (formData.start_date > formData.end_date) {
      validationErrors.start_date.addError(
        "Start date must be before end date, please fix.",
      );
    }
    return validationErrors;
  }

  const allocationFormSchema = {
    type: "object",
    properties: {
      types: {
        type: "array",
        title: "Types",
        items: {
          type: "string",
          enum: allowedAllocationTypes,
        },
        uniqueItems: true,
        default: allocationLookUp[allocation_id]?.types,
      },
      pi: {
        type: "string",
        title: "PI",
        default: allocationLookUp[allocation_id]?.pi,
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
        default: allocationLookUp[allocation_id]?.hours_allocated,
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
      <Controller
        name="group"
        render={({ field: { onChange } }) => (
          <Autocomplete
            id="addGroup"
            onChange={(e, data) => {
              setSelectedGroup(data);
              onChange(data);
            }}
            style={{ marginTop: "0.1rem" }}
            value={selectedGroup}
            options={groups}
            getOptionLabel={(thisGroup) => thisGroup.name}
            filterSelectedOptions
            data-testid="addGroup"
            renderInput={(field) => (
              <TextField
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
        defaultValue={selectedGroup}
        rules={{ validate: validateGroup }}
      />
      <div>
        {group?.users && (
          <>
            <Controller
              name="users"
              render={({ field: { onChange } }) => (
                <Autocomplete
                  multiple
                  id="addUsersFromGroupSelect"
                  onChange={(e, data) => {
                    setSelectedUsers(data);
                    onChange(data);
                  }}
                  value={selectedUsers}
                  options={group?.users}
                  getOptionLabel={(user) => userLabel(user)}
                  filterSelectedOptions
                  data-testid="addUsersFromGroupSelect"
                  renderInput={(field) => (
                    <TextField
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

ModifyAllocation.propTypes = {
  allocation_id: PropTypes.number.isRequired,
  onClose: PropTypes.func,
};

ModifyAllocation.defaultProps = {
  onClose: null,
};

export default ModifyAllocation;
