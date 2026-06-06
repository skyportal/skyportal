import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import {
  useSubmitInstrumentMutation,
  useModifyInstrumentMutation,
} from "../../ducks/instrument";
import { useGetFollowupApisQuery } from "../../ducks/followupApis";

interface InstrumentFormProps {
  onClose: () => void;
  instrumentId?: number | null;
}

const InstrumentForm = ({
  onClose,
  instrumentId = null,
}: InstrumentFormProps) => {
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: followupApis } = useGetFollowupApisQuery();
  const { enum_types } = useAppSelector((state) => state["enum_types"]);
  const [formData, setFormData] = useState<any>({});
  const dispatch = useAppDispatch();
  const [submitInstrument] = useSubmitInstrumentMutation();
  const [modifyInstrument] = useModifyInstrumentMutation();

  const handleSubmit = async () => {
    const dataToSubmit: any = { ...formData };
    const keys = Object.keys(dataToSubmit);
    if (keys.includes("field_data") && dataToSubmit.field_data) {
      const parsed_field_data = dataUriToBuffer(dataToSubmit.field_data);
      dataToSubmit.field_data = new TextDecoder().decode(
        parsed_field_data.buffer,
      );
    }
    if (keys.includes("field_region") && dataToSubmit.field_region) {
      const parsed_field_region = dataUriToBuffer(dataToSubmit.field_region);
      dataToSubmit.field_region = new TextDecoder().decode(
        parsed_field_region.buffer,
      );
    }
    if (keys.includes("references") && dataToSubmit.references) {
      const parsed_references = dataUriToBuffer(dataToSubmit.references);
      dataToSubmit.references = new TextDecoder().decode(
        parsed_references.buffer,
      );
    }
    dataToSubmit.field_fov_attributes =
      dataToSubmit.field_fov_attributes?.split(",");

    if (dataToSubmit.specific_configuration) {
      try {
        dataToSubmit.configuration_data = {
          ...JSON.parse(dataToSubmit.configuration_data || "{}"),
          specific_configuration: dataToSubmit.specific_configuration,
        };
      } catch (e) {
        dispatch(
          showNotification(
            "Error, configuration data is not valid JSON",
            "error",
          ),
        );
        return;
      }
      delete dataToSubmit.specific_configuration;
    }

    try {
      if (instrumentId) {
        await modifyInstrument({
          id: instrumentId,
          params: dataToSubmit,
        }).unwrap();
      } else {
        await submitInstrument(dataToSubmit).unwrap();
      }
      dispatch(showNotification("Instrument saved"));
      onClose();
    } catch {
      // error notification handled by the base query
    }
  };

  if (instrumentList.length === 0 || telescopeList.length === 0) {
    return <h3>No instruments available...</h3>;
  } else if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const api_classnames = [...enum_types.ALLOWED_API_CLASSNAMES].sort();
  const filters = [...enum_types.ALLOWED_BANDPASSES].sort();

  const instrumentToEdit = instrumentId
    ? instrumentList.find((inst: any) => inst.id === instrumentId)
    : null;
  if (instrumentId && !instrumentToEdit) {
    return <h3>Instrument not found !</h3>;
  }

  function validate(dataToCheck: any, errors: any) {
    if (dataToCheck.configuration_data) {
      try {
        JSON.parse(dataToCheck.configuration_data);
      } catch (e) {
        errors.configuration_data.addError(
          "Configuration data is not valid JSON",
        );
      }
    }
    if (
      instrumentId === null &&
      instrumentList?.some(
        (instrument: any) => dataToCheck.name === instrument.name,
      )
    ) {
      errors.name.addError("Instrument name matches another, please change.");
    }
    if (dataToCheck.field_region && dataToCheck.field_fov_type) {
      errors.field_region.addError(
        "Must only choose either field_region or field_fov_type.",
      );
    }
    if (dataToCheck.field_fov_type && dataToCheck.field_fov_attributes) {
      const attributes = dataToCheck.field_fov_attributes.split(",");
      if (dataToCheck.field_fov_type === "circle" && attributes.length !== 1) {
        errors.field_fov_attributes.addError(
          "For the circle option, field_fov_attributes should be a single number (radius in degrees).",
        );
      } else if (
        dataToCheck.field_fov_type === "rectangle" &&
        attributes.length !== 2
      ) {
        errors.field_fov_attributes.addError(
          "For the rectangle option, field_fov_attributes should be two numbers (width and height in degrees).",
        );
      }
    }
    return errors;
  }

  const getDefaultConfigurationData = () => {
    const { specific_configuration, ...configuration } =
      instrumentToEdit?.configuration_data || {};
    if (configuration && Object.keys(configuration).length > 0) {
      return configuration;
    }
    return undefined;
  };

  const instrumentFormSchema: any = {
    type: "object",
    properties: {
      ...(instrumentToEdit
        ? {}
        : {
            name: {
              type: "string",
              title: "Name",
            },
            telescope_id: {
              type: "integer",
              oneOf: telescopeList.map((telescope: any) => ({
                enum: [telescope.id],
                title: `${telescope.name}`,
              })),
              title: "Telescope",
            },
            treasuremap_id: {
              type: "integer",
              title: "Treasuremap ID",
              description:
                "ID of the instrument to submit to Treasuremap (optional)",
            },
            type: {
              type: "string",
              oneOf: [
                { enum: ["imager"], title: "Imager" },
                {
                  enum: ["imaging spectrograph"],
                  title: "Imaging Spectrograph",
                },
                { enum: ["spectrograph"], title: "Spectrograph" },
              ],
              title: "Type",
            },
            band: {
              type: "string",
              title: "Band (e.g., Optical, IR)",
            },
          }),
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
        default: instrumentToEdit?.filters || [],
      },
      api_classname: {
        type: "string",
        enum: api_classnames,
        uniqueItems: true,
        title: "API Classname",
        default: instrumentToEdit?.api_classname || undefined,
      },
      api_classname_obsplan: {
        type: "string",
        enum: api_classnames,
        uniqueItems: true,
        title: "API Observation Plan Classname",
        default: instrumentToEdit?.api_classname_obsplan || undefined,
      },
      field_data: {
        type: "string",
        format: "data-url",
        title: "Field data file",
        description: "Field data file",
      },
      field_region: {
        type: "string",
        format: "data-url",
        title: "Field region file",
        description: "Field region file",
      },
      references: {
        type: "string",
        format: "data-url",
        title: "References file",
        description: "References file",
      },
      field_fov_type: {
        type: "string",
        oneOf: [
          {
            enum: ["rectangle"],
            title: "rectangle",
          },
          {
            enum: ["circle"],
            title: "circle",
          },
        ],
        uniqueItems: true,
        title: "FOV Type",
        description: "Rectangle or Circle",
      },
      field_fov_attributes: {
        type: "string",
        title: "FOV Attributes",
        description: "Rectangle: width,height; Circle: radius",
      },
      sensitivity_data: {
        type: "string",
        title:
          "Sensitivity data i.e. {'ztfg': {'limiting_magnitude': 20.3, 'magsys': 'ab', 'exposure_time': 30, 'zeropoint': 26.3,}}",
        default: JSON.stringify(
          instrumentToEdit?.sensitivity_data || undefined,
        ),
      },
      configuration_data: {
        type: "string",
        title:
          "Configuration data i.e. {'overhead_per_exposure': 2.0, 'readout': 8.0, 'slew_rate': 2.6, 'filt_change_time': 60.0}",
        default: JSON.stringify(getDefaultConfigurationData()),
      },
      ...(followupApis?.[formData.api_classname]?.formSchemaConfig?.properties
        ? {
            specific_configuration: {
              type: "object",
              title: "Specific API configuration",
              properties: {
                ...followupApis[formData.api_classname].formSchemaConfig
                  .properties,
              },
              default:
                instrumentToEdit?.configuration_data?.specific_configuration ||
                {},
            },
          }
        : {}),
    },
    ...(instrumentId
      ? {}
      : { required: ["name", "type", "band", "telescope_id"] }),
  };

  const uiSchema = {
    api_classname: {
      "ui:placeholder": "Choose an option",
    },
    api_classname_obsplan: {
      "ui:placeholder": "Choose an option",
    },
    field_fov_type: {
      "ui:placeholder": "Choose an option",
    },
  };

  return (
    <Form
      schema={instrumentFormSchema as any}
      validator={validator}
      onSubmit={handleSubmit}
      customValidate={validate}
      formData={formData}
      onChange={(e) => setFormData(e.formData)}
      uiSchema={uiSchema}
    />
  );
};

export default InstrumentForm;
