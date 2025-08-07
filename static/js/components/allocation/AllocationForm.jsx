import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import IconButton from "@mui/material/IconButton";
import { AddCircle, ArrowDropDown, Delete } from "@mui/icons-material";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import Popover from "@mui/material/Popover";
import Chip from "@mui/material/Chip";
import Button from "../Button";
import { modifyAllocation, submitAllocation } from "../../ducks/allocation";
import { fetchAllocations } from "../../ducks/allocations";
import GroupShareSelect from "../group/GroupShareSelect";
import { userLabel } from "../../utils/format";

dayjs.extend(utc);

const ValidityRangeSelect = ({ ranges = [], onChange, errors, setErrors }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const selectRef = useRef();
  const handleOpen = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const validateRanges = (rangesToProcess) => {
    let newErrors = {};
    rangesToProcess.forEach((range, index) => {
      const startDate = dayjs(range.start_date);
      const endDate = dayjs(range.end_date);
      if (startDate.isAfter(endDate)) {
        newErrors[index] = "Start date must be before end date";
      } else if (
        index > 0 &&
        startDate.isBefore(dayjs(ranges[index - 1].end_date))
      ) {
        newErrors[index] = "Start date must be after previous range's end date";
      } else {
        newErrors[index] = null;
      }
    });
    setErrors(newErrors);
  };

  useEffect(() => {
    validateRanges(ranges);
  }, [ranges]);

  const handleUpdate = (index, field, newValue) => {
    const newRanges = [...ranges];
    newRanges[index][field] = newValue;
    onChange(newRanges);
  };

  const handleDelete = (index) => {
    onChange(ranges.filter((_, i) => i !== index));
  };

  const handleAdd = () => {
    // If there are existing ranges, start when the last one ends if not, start now
    let defaultStart = dayjs();
    onChange([
      ...ranges,
      {
        start_date: defaultStart.toISOString(),
        end_date: defaultStart.add(365, "day").toISOString(),
      },
    ]);
  };

  const [selectWidth, setSelectWidth] = useState(null);

  useEffect(() => {
    const updateWidth = () => {
      if (selectRef.current) {
        setSelectWidth(selectRef.current.offsetWidth);
      }
    };

    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <FormControl fullWidth ref={selectRef}>
        <InputLabel id="validity-label">Validity Ranges</InputLabel>
        <Select
          labelId="validity-label"
          label="Validity Ranges"
          value={ranges.length ? "ranges" : ""}
          open={false}
          renderValue={() => (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {ranges.map((range) => (
                <Chip
                  key={`${range.start_date}-${range.end_date}`}
                  label={`${dayjs(range.start_date).format(
                    "YYYY-MM-DD",
                  )} - ${dayjs(range.end_date).format("YYYY-MM-DD")}`}
                  color={
                    range.start_date < dayjs().toISOString() &&
                    range.end_date > dayjs().toISOString()
                      ? "success"
                      : "default"
                  }
                />
              ))}
            </Box>
          )}
          onClick={handleOpen}
          IconComponent={ArrowDropDown}
        ></Select>
        <Typography variant="body2" color="text.secondary.dark">
          Define time ranges to control when this allocation can be used. It
          will not be available outside these ranges. (Local timezone)
        </Typography>
        <Popover
          open={open}
          anchorEl={anchorEl}
          onClose={handleClose}
          anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
          slotProps={{
            paper: {
              sx: { width: selectWidth ?? 500 },
            },
          }}
        >
          <Box sx={{ p: 2, minWidth: 500 }}>
            {ranges.map((range, index) => (
              <Box key={index} sx={{ mb: 2 }}>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <DateTimePicker
                    ampm={false}
                    label="Start"
                    value={new Date(range.start_date)}
                    onChange={(val) =>
                      handleUpdate(index, "start_date", val.toISOString())
                    }
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: "small",
                        error: !!errors[index],
                      },
                    }}
                  />
                  <DateTimePicker
                    ampm={false}
                    label="End"
                    value={new Date(range.end_date)}
                    onChange={(val) =>
                      handleUpdate(index, "end_date", val.toISOString())
                    }
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: "small",
                        error:
                          index in errors &&
                          errors[index] &&
                          !errors[index].includes("previous"),
                      },
                    }}
                  />
                  <IconButton onClick={() => handleDelete(index)} color="error">
                    <Delete />
                  </IconButton>
                </Box>
                {errors[`${index}`] && (
                  <Typography color="error" variant="body2">
                    {errors[`${index}`]}
                  </Typography>
                )}
              </Box>
            ))}
            <Button
              endIcon={<AddCircle />}
              onClick={handleAdd}
              variant="outlined"
              size="small"
            >
              Add Range
            </Button>
          </Box>
        </Popover>
      </FormControl>
    </LocalizationProvider>
  );
};

ValidityRangeSelect.propTypes = {
  ranges: PropTypes.arrayOf(
    PropTypes.shape({
      start_date: PropTypes.string.isRequired,
      end_date: PropTypes.string.isRequired,
    }),
  ),
  onChange: PropTypes.func.isRequired,
  errors: PropTypes.shape({}).isRequired,
  setErrors: PropTypes.func.isRequired,
};

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
  const [allocationToEdit, setAllocationToEdit] = useState(null);
  const [rangeErrors, setRangeErrors] = useState({});
  // Default validity range to one year from now if creating a new allocation
  const [formData, setFormData] = useState(
    allocationId
      ? {}
      : {
          validity_ranges: [
            {
              start_date: dayjs().toISOString(),
              end_date: dayjs().add(365, "day").toISOString(),
            },
          ],
        },
  );

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
    if (selectedGroupIds.length > 0) {
      formData.default_share_group_ids = selectedGroupIds;
    }
    const result = await dispatch(
      allocationId == null
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
    const error = Object.values(rangeErrors || {}).find(Boolean);
    if (error) {
      errors.validity_ranges.addError(error);
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
        default: allocationToEdit?.group_id || "",
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
      hours_allocated: {
        type: "number",
        title: "Hours allocated",
        default: allocationToEdit?.hours_allocated,
      },
      instrument_id: {
        type: "integer",
        oneOf: instrumentOptions.map((instrument) => ({
          enum: [instrument.value],
          title: instrument.label,
        })),
        title: "Instrument",
        default: allocationToEdit?.instrument_id || "",
      },
      ...(instrumentForm?.formSchemaAltdata?.properties
        ? {
            _altdata: {
              type: "object",
              title: "Allocation Parameters/Credentials",
              properties: instrumentForm.formSchemaAltdata.properties,
              // If allocation already exists, altdata is optional
              required:
                allocationId === null
                  ? instrumentForm.formSchemaAltdata.required
                  : [],
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
    required: ["group_id", "pi", "instrument_id", "hours_allocated"],
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
      <ValidityRangeSelect
        ranges={
          formData.validity_ranges || allocationToEdit?.validity_ranges || []
        }
        onChange={(ranges) =>
          setFormData({ ...formData, validity_ranges: ranges })
        }
        errors={rangeErrors}
        setErrors={setRangeErrors}
      />
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
