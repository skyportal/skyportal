import { useState } from "react";
import ButtonGroup from "@mui/material/ButtonGroup";
import TextField from "@mui/material/TextField";
import Divider from "@mui/material/Divider";
import Box from "@mui/material/Box";
import { Controller, useForm } from "react-hook-form";
import Button from "../Button";

import GcnTagsSelect from "./GcnTagsSelect";
import GcnPropertiesSelect from "./GcnPropertiesSelect";
import LocalizationTagsSelect from "../localization/LocalizationTagsSelect";
import LocalizationPropertiesSelect from "../localization/LocalizationPropertiesSelect";

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

interface GcnEventsFilterFormProps {
  handleFilterSubmit: (...args: any[]) => void;
}

const GcnEventsFilterForm = ({
  handleFilterSubmit,
}: GcnEventsFilterFormProps) => {
  const [selectedGcnTags, setSelectedGcnTags] = useState<any[]>([]);
  const [rejectedGcnTags, setRejectedGcnTags] = useState<any[]>([]);
  const [selectedGcnProperties, setSelectedGcnProperties] = useState<any[]>([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState<
    any[]
  >([]);
  const [rejectedLocalizationTags, setRejectedLocalizationTags] = useState<
    any[]
  >([]);
  const [selectedLocalizationProperties, setSelectedLocalizationProperties] =
    useState<any[]>([]);

  const { handleSubmit, register: _register, control, reset } = useForm();

  const handleClickReset = () => {
    reset({ startDate: "", endDate: "" });
    setSelectedGcnTags([]);
    setRejectedGcnTags([]);
    setSelectedGcnProperties([]);
    setSelectedLocalizationTags([]);
    setRejectedLocalizationTags([]);
    setSelectedLocalizationProperties([]);
  };

  const handleFilterPreSubmit = (formData: any) => {
    handleFilterSubmit({
      startDate: formData.startDate,
      endDate: formData.endDate,
      gcnTagKeep: selectedGcnTags,
      gcnTagRemove: rejectedGcnTags,
      gcnPropertiesFilter: selectedGcnProperties,
      localizationTagKeep: selectedLocalizationTags,
      localizationTagRemove: rejectedLocalizationTags,
      localizationPropertiesFilter: selectedLocalizationProperties,
    });
  };

  return (
    <Box
      sx={{
        paddingTop: "1rem",
        gap: "0.8rem",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box display="flex" gap="0.2rem">
        <Controller
          name="startDate"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="First Detected After (UTC)"
              placeholder="2012-08-30T00:00:00"
              fullWidth
            />
          )}
        />
        <Controller
          name="endDate"
          control={control}
          render={({ field }) => (
            <TextField
              {...field}
              label="Last Detected Before (UTC)"
              placeholder="2012-08-30T00:00:00"
              fullWidth
            />
          )}
        />
      </Box>
      <Divider />
      <Box display="flex" gap="0.2rem">
        <GcnTagsSelect
          title="GCN Tags to Keep"
          selectedGcnTags={selectedGcnTags}
          setSelectedGcnTags={setSelectedGcnTags}
        />
        <GcnTagsSelect
          title="GCN Tags to Reject"
          selectedGcnTags={rejectedGcnTags}
          setSelectedGcnTags={setRejectedGcnTags}
        />
      </Box>
      <GcnPropertiesSelect
        selectedGcnProperties={selectedGcnProperties}
        setSelectedGcnProperties={setSelectedGcnProperties}
        conversions={conversions}
        comparators={comparators}
      />
      <Divider />
      <Box display="flex" gap="0.2rem">
        <LocalizationTagsSelect
          title="Localization Tags to Keep"
          selectedLocalizationTags={selectedLocalizationTags}
          setSelectedLocalizationTags={setSelectedLocalizationTags}
        />
        <LocalizationTagsSelect
          title="Localization Tags to Reject"
          selectedLocalizationTags={rejectedLocalizationTags}
          setSelectedLocalizationTags={setRejectedLocalizationTags}
        />
      </Box>
      <LocalizationPropertiesSelect
        selectedLocalizationProperties={selectedLocalizationProperties}
        setSelectedLocalizationProperties={setSelectedLocalizationProperties}
        comparators={comparators}
      />
      <ButtonGroup variant="outlined" color="primary">
        <Button primary onClick={handleSubmit(handleFilterPreSubmit)}>
          Submit
        </Button>
        <Button primary onClick={handleClickReset}>
          Reset
        </Button>
      </ButtonGroup>
    </Box>
  );
};

export default GcnEventsFilterForm;
