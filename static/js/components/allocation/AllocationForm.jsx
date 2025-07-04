import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { modifyAllocation, submitAllocation } from "../../ducks/allocation";
import { fetchAllocations } from "../../ducks/allocations";
import GroupShareSelect from "../group/GroupShareSelect";
import Box from "@mui/material/Box";
import { userLabel } from "../../utils/format";

dayjs.extend(utc);

const format = (date) => date.utc().format("YYYY-MM-DDTHH:mm:ssZ");

const AllocationForm = ({ onClose, allocationId }) => {
  const dispatch = useDispatch();
  const { allocationList } = useSelector((state) => state.allocations);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );
  const allowedAllocationTypes = useSelector(
    (state) => state.config.allowedAllocationTypes,
  );
  const groups = useSelector((state) => state.groups.userAccessible);
  const { users } = useSelector((state) => state.users);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [instrumentOptions, setInstrumentOptions] = useState([]);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [formData, setFormData] = useState({});
  const [allocationToEdit, setAllocationToEdit] = useState(null);

  useEffect(() => {
    setAvailableUsers(
      users.filter(
        (user) =>
          user.groups?.some((g) => g.id === formData.group_id) && !user.is_bot,
      ),
    );
  }, [users, formData.group_id]);

  useEffect(() => {
    if (instrumentList?.length > 0) {
      let options = instrumentList.map((instrument) => ({
        value: instrument.id,
        label: `${instrument?.telescope?.name} / ${instrument.name}`,
      }));
      options = options.sort((a, b) => a.label.localeCompare(b.label));
      setInstrumentOptions(options);
    }
  }, [instrumentList]);

  useEffect(() => {
    if (allocationId) {
      const allocation = allocationList.find(
        (alloc) => alloc.id === allocationId,
      );
      if (allocation) {
        setAllocationToEdit(allocation);
        setSelectedGroupIds(allocation.default_share_group_ids || []);
      }
    }
  }, [allocationId, allocationList]);

  const handleSubmit = async () => {
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    if (selectedGroupIds.length > 0) {
      formData.default_share_group_ids = selectedGroupIds;
    }
    const result = await dispatch(
      allocationId === null
        ? submitAllocation(formData)
        : modifyAllocation(allocationId, formData),
    );
    if (result.status === "success") {
      dispatch(showNotification("Allocation saved"));
      dispatch(fetchAllocations());
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  function validate(_, errors) {
    if (format(dayjs()) > formData.end_date) {
      errors.end_date.addError(
        "End date must be after current time, please fix.",
      );
    }
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix.",
      );
    }
    return errors;
  }

  const instrumentForm =
    formData.instrument_id !== null &&
    instrumentFormParams[formData.instrument_id];
  const allocationFormSchema = {
    type: "object",
    properties: {
      group_id: {
        type: "integer",
        oneOf: (groups || []).map((group) => ({
          enum: [group.id],
          type: "integer",
          title: `${group.name}`,
        })),
        title: "Group",
        default: allocationToEdit?.group_id || null,
      },
      ...(availableUsers.length > 0 && {
        allocation_admin_ids: {
          type: "array",
          title: "Allocation admins",
          items: {
            oneOf: availableUsers.map((user) => ({
              const: user.id,
              title: userLabel(user, true, true),
            })),
          },
          uniqueItems: true,
          default:
            allocationToEdit?.allocation_users.map((user) => user.id) || [],
        },
      }),
      types: {
        type: "array",
        title: "Types",
        items: {
          type: "string",
          enum: allowedAllocationTypes,
        },
        uniqueItems: true,
        default: allocationToEdit?.types || [],
      },
      pi: {
        type: "string",
        title: "PI",
        default: allocationToEdit?.pi || "",
      },
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date (Local Time)",
        default: allocationToEdit
          ? format(dayjs(`${allocationToEdit.start_date}Z`))
          : format(dayjs()),
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date (Local Time)",
        default: allocationToEdit
          ? format(dayjs(`${allocationToEdit.end_date}Z`))
          : format(dayjs().add(365, "day")),
      },
      hours_allocated: {
        type: "number",
        title: "Hours allocated",
        default: allocationToEdit?.hours_allocated || 0,
      },
      instrument_id: {
        type: "integer",
        oneOf: instrumentOptions.map((instrument) => ({
          enum: [instrument.value],
          title: instrument.label,
        })),
        title: "Instrument",
        default: allocationToEdit?.instrument_id || null,
      },
      ...(instrumentForm?.formSchemaAltdata?.properties
        ? {
            _altdata: {
              type: "object",
              title: "Allocation Parameters/Credentials",
              properties: instrumentForm.formSchemaAltdata.properties,
              // If allocation already exists, altdata is optional
              required:
                (allocationId === null &&
                  instrumentForm.formSchemaAltdata.required) ||
                [],
              dependencies: instrumentForm.formSchemaAltdata.dependencies || {},
            },
            ...(allocationId !== null && {
              replace_altdata: {
                type: "boolean",
                title:
                  "Overwrite all allocation parameters (if false, only update specified allocation parameters)",
                default: false,
              },
            }),
          }
        : {
            _altdata: {
              type: "string",
              title:
                "Allocation Parameters/Credentials json (i.e. {'slack_token': 'testtoken'}",
            },
          }),
    },
    required: [
      "group_id",
      "pi",
      "start_date",
      "end_date",
      "instrument_id",
      "hours_allocated",
    ],
  };

  if (!groups || !instrumentOptions?.length > 0) {
    return (
      <Box sx={{ textAlign: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (allocationId && !allocationToEdit) {
    return <h3>Allocation not found</h3>;
  }

  return (
    <div style={{ position: "relative" }}>
      <Form
        schema={allocationFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        customValidate={validate}
        formData={formData}
        onChange={(e) => setFormData(e.formData)}
      />
      <div style={{ position: "absolute", bottom: "0", right: "0" }}>
        <GroupShareSelect
          groupList={groups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
      </div>
    </div>
  );
};

AllocationForm.propTypes = {
  onClose: PropTypes.func,
  allocationId: PropTypes.number,
};

AllocationForm.defaultProps = {
  allocationId: null,
};

export default AllocationForm;
