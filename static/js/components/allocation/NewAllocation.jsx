import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import makeStyles from "@mui/styles/makeStyles";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { submitAllocation } from "../../ducks/allocation";
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

const NewAllocation = ({ onClose }) => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const allowedAllocationTypes = useSelector(
    (state) => state.config.allowedAllocationTypes,
  );
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

  const validateGroup = () => {
    const formState = getValues();
    return formState.group.length === 1;
  };

  const validateUsers = () => {
    const formState = getValues();
    return formState.users.length >= 0;
  };

  useEffect(() => {
    if (selectedGroup) {
      dispatch(groupActions.fetchGroup(selectedGroup.id));
    }
  }, [selectedGroup, dispatch]);

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
    const result = await dispatch(submitAllocation(formData));
    if (result.status === "success") {
      dispatch(showNotification("Allocation saved"));
      dispatch(fetchAllocations());
      if (typeof onClose === "function") {
        onClose();
      }
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
      },
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
      instrument_id: {
        type: "integer",
        oneOf: instrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${
            telescopeList.find(
              (telescope) => telescope.id === instrument.telescope_id,
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      _altdata: {
        type: "string",
        title: "Alternative json data (i.e. {'slack_token': 'testtoken'}",
      },
    },
    required: [
      "pi",
      "start_date",
      "end_date",
      "instrument_id",
      "hours_allocated",
    ],
  };

  return (
    <div>
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
        customValidate={validate}
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

NewAllocation.propTypes = {
  onClose: PropTypes.func,
};

NewAllocation.defaultProps = {
  onClose: null,
};

export default NewAllocation;
