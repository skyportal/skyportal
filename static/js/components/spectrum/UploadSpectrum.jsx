import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link, useSearchParams } from "react-router-dom";
import MUIDataTable from "mui-datatables";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import Grid from "@mui/material/Grid";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import CircularProgress from "@mui/material/CircularProgress";
import embed from "vega-embed";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { showNotification } from "baselayer/components/Notifications";

import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Button from "../Button";

import withRouter from "../withRouter";

import * as spectraActions from "../../ducks/spectra";
import { fetchSource } from "../../ducks/source";
import { fetchUsers } from "../../ducks/users";
import { userLabel } from "../../utils/format";
import Paper from "../Paper";
import Spinner from "../Spinner";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import VisibilityIcon from "@mui/icons-material/Visibility";

dayjs.extend(utc);

const spectrumPreviewSpec = (data) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
  width: "container",
  height: 200,
  data: { values: data },
  mark: "line",
  encoding: {
    x: {
      field: "wavelength",
      type: "quantitative",
      title: "Wavelength (Angstroms)",
    },
    y: { field: "flux", type: "quantitative", axis: { format: ".2e" } },
  },
});

const SpectrumPreview = React.memo(({ data }) => {
  return (
    <Box
      ref={(node) => {
        if (node) embed(node, spectrumPreviewSpec(data), { actions: false });
      }}
      sx={{ width: "100%" }}
    />
  );
});

SpectrumPreview.displayName = "SpectrumPreview";
SpectrumPreview.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      wavelength: PropTypes.number,
      flux: PropTypes.number,
      error: PropTypes.number,
    }),
  ).isRequired,
};

const UploadSpectrumForm = ({ route }) => {
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.all);
  const { parsed } = useSelector((state) => state.spectra);
  const { users } = useSelector((state) => state.users);
  const instrumentList = useSelector(
    (state) => state.instruments.instrumentList,
  );
  const telescopes = useSelector((state) => state.telescopes.telescopeList);
  const source = useSelector((state) => state.source);
  const [persistentFormData, setPersistentFormData] = useState({});
  const [formKey, setFormKey] = useState(null);
  const [header, setHeader] = useState([]);
  const [data, setData] = useState([]);
  const [headerHasComments, setHeaderHasComments] = useState(false);
  const spectrumTypes = useSelector(
    (state) => state.config.allowedSpectrumTypes,
  );

  const defaultSpectrumType = useSelector(
    (state) => state.config.defaultSpectrumType,
  );
  const [searchParams] = useSearchParams();
  const [uploadedFromURL, setUploadedFromURL] = useState(false);
  const [userEnumOptions, setUserEnumOptions] = useState([]);

  useEffect(() => {
    if (!users?.length) return;

    setUserEnumOptions({
      enum: users.map((user) => user.id),
      enumNames: users.map((user) => userLabel(user, true)),
    });
  }, [users]);

  const unwrapQuotes = (str) =>
    str && str.startsWith('"') && str.endsWith('"') ? str.slice(1, -1) : str;

  // utility to get a list of integers from a comma-separated URL parameter
  const getIntList = (param) =>
    searchParams
      .get(param)
      ?.split(",")
      .map((id) => parseInt(id, 10));

  // on page load or refresh, block until state.spectra.parsed is reset
  useEffect(() => {
    (async () => {
      dispatch({ type: spectraActions.RESET_PARSED_SPECTRUM });

      const [_, sourceResult] = await Promise.all([
        dispatch(fetchUsers()),
        dispatch(fetchSource(route.id)),
      ]);

      let file;
      const fileUrl = unwrapQuotes(searchParams.get("file_url"));
      const fileName = unwrapQuotes(searchParams.get("file_name"));

      if (fileUrl) {
        const response = await fetch(fileUrl);
        const blob = await response.blob();
        const reader = new FileReader();
        // we want to set the file to a data url, so we can pass it to the form
        file = await new Promise((resolve) => {
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(blob);
        });
        if (!file.includes("name=")) {
          const type = file.split(";")[0].split(":")[1];
          file = file.replace(type, `${type};name=${fileName}`);
        }
        setUploadedFromURL(true);
      }

      setPersistentFormData({
        file,
        group_ids:
          getIntList("group_ids") ?? sourceResult.data.groups?.map((g) => g.id),
        mjd: parseFloat(searchParams.get("mjd")) || undefined,
        wave_column: parseInt(searchParams.get("wave_column"), 10) || 0,
        flux_column: parseInt(searchParams.get("flux_column"), 10) || 1,
        fluxerr_column:
          parseInt(searchParams.get("fluxerr_column"), 10) || undefined,
        has_fluxerr: searchParams.get("has_fluxerr") || "No",
        instrument_id:
          parseInt(searchParams.get("instrument_id"), 10) || undefined,
        spectrum_type: searchParams.get("spectrum_type") || "source",
        user_label: searchParams.get("user_label") || undefined,
        observed_by: getIntList("observed_by"),
        reduced_by: getIntList("reduced_by"),
      });
    })();
  }, [dispatch, route.id, searchParams]);

  useEffect(() => {
    if (!parsed) return;

    let newData = [];
    let hasComments = false;
    const newHeader = parsed.altdata
      ? Object.entries(parsed.altdata).map(([key, value]) => {
          if (value && typeof value === "object") {
            hasComments = true;
            return { key, value: value.value, comment: value.comment };
          }
          return { key, value };
        })
      : [];

    if (hasComments) {
      // Set default comment to null if not present
      newHeader.forEach((obj) => (obj.comment ??= null)); // Assign only if the left side is null or undefined
    }
    parsed.wavelengths.forEach((w, i) => {
      const datum = {
        flux: parsed.fluxes[i],
        wavelength: w,
        ...(parsed.errors?.[i] && { error: parsed.errors[i] }),
      };
      newData.push(datum);
    });
    setHeaderHasComments(hasComments);
    setHeader(newHeader);
    setData(newData);
  }, [parsed]);

  if (
    !groups ||
    !instrumentList ||
    !telescopes ||
    !users.length ||
    source.id !== route.id
  ) {
    return <Spinner />;
  }

  const instruments = instrumentList.filter((i) => i.type.includes("spec"));

  const header_columns = [
    {
      name: "key",
      label: "Key",
      options: {
        filter: true,
        sort: true,
      },
    },
    {
      name: "value",
      label: "Value",
      options: {
        filter: true,
        sort: true,
      },
    },
    ...(headerHasComments
      ? [
          {
            name: "comment",
            label: "Comment",
            options: { filter: false, sort: true },
          },
        ]
      : []),
  ];

  const data_columns = [
    {
      name: "wavelength",
      label: "Wavelength (Angstroms)",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "flux",
      label: "Flux",
      options: {
        filter: false,
        sort: true,
      },
    },
    ...(parsed?.errors
      ? [
          {
            name: "error",
            label: "Flux Error",
            options: {
              filter: false,
              sort: true,
            },
          },
        ]
      : []),
  ];

  const uploadFormSchema = {
    type: "object",
    properties: {
      group_ids: {
        type: "array",
        title: "Share with...",
        items: {
          type: "integer",
          enum: groups.map((group) => group.id),
        },
        uniqueItems: true,
      },
      file: {
        type: "string",
        format: "data-url",
        title: "Spectrum file",
      },
      mjd: {
        type: "number",
        title: "Observation MJD",
      },
      instrument_id: {
        type: "integer",
        title: "Instrument",
        ...(instruments?.length
          ? {
              enum: instruments.map((instrument) => instrument.id),
            }
          : {}),
      },
      spectrum_type: {
        type: "string",
        default: defaultSpectrumType,
        title: "Spectrum type",
        enum: spectrumTypes,
      },
      observer_mode: {
        type: "string",
        default: "User",
        title: "Observer type",
        enum: ["User", "External"],
      },
      reducer_mode: {
        type: "string",
        default: "User",
        title: "Reducer type",
        enum: ["User", "External"],
      },
      pi_mode: {
        type: "string",
        default: "User",
        title: "PI type",
        enum: ["User", "External"],
      },
      wave_column: {
        type: "integer",
        default: 0,
        title: "0-Based Wavelength Column Index",
      },
      flux_column: {
        type: "integer",
        default: 1,
        title: "0-Based Flux Column Index",
      },
      has_fluxerr: {
        type: "string",
        default: "No",
        title: "Does your spectrum have flux errors?",
        enum: ["No", "Yes"],
      },
      user_label: {
        type: "string",
        title: "User label",
        default: "",
      },
    },
    required: [
      "file",
      "has_fluxerr",
      "mjd",
      "wave_column",
      "flux_column",
      "instrument_id",
    ],
    dependencies: {
      pi_mode: {
        oneOf: [
          {
            properties: {
              pi_mode: {
                enum: ["User"],
              },
              pi: {
                type: "array",
                title: "PI(s)",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
          },
          {
            properties: {
              pi_mode: {
                enum: ["External"],
              },
              pi: {
                type: "string",
                title: "PI(s)",
              },
              pi_point_of_contact: {
                type: "array",
                title: "Point of contact user for PI(s)",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
            required: ["pi_mode", "pi", "pi_point_of_contact"],
          },
        ],
      },
      reducer_mode: {
        oneOf: [
          {
            properties: {
              reducer_mode: {
                enum: ["User"],
              },
              reduced_by: {
                type: "array",
                title: "Reducers",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
          },
          {
            properties: {
              reducer_mode: {
                enum: ["External"],
              },
              reduced_by: {
                type: "string",
                title: "Reducers",
              },
              reducer_point_of_contact: {
                type: "array",
                title: "Point of contact user for reducers",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
            required: [
              "reducer_mode",
              "reduced_by",
              "reducer_point_of_contact",
            ],
          },
        ],
      },
      observer_mode: {
        oneOf: [
          {
            properties: {
              observer_mode: {
                enum: ["User"],
              },
              observed_by: {
                type: "array",
                title: "Observers",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
          },
          {
            properties: {
              observer_mode: {
                enum: ["External"],
              },
              observed_by: {
                type: "string",
                title: "Observers",
              },
              observer_point_of_contact: {
                type: "array",
                title: "Point of contact user for observers",
                items: {
                  type: "integer",
                  enum: userEnumOptions?.enum,
                },
                uniqueItems: true,
              },
            },
            required: [
              "observer_mode",
              "observed_by",
              "observer_point_of_contact",
            ],
          },
        ],
      },
      has_fluxerr: {
        oneOf: [
          {
            properties: {
              has_fluxerr: {
                enum: ["No"],
              },
            },
          },
          {
            properties: {
              has_fluxerr: {
                enum: ["Yes"],
              },
              fluxerr_column: {
                type: "integer",
                default: null,
                title: "0-Based Flux Error Column Index",
              },
            },
            required: ["has_fluxerr", "fluxerr_column"],
          },
        ],
      },
    },
  };

  const uiSchema = {
    group_ids: {
      "ui:enumNames": groups.map((group) => group.name),
    },
    instrument_id: {
      "ui:enumNames": instruments.map(
        (instrument) =>
          `${
            telescopes.find((t) => t.id === instrument.telescope_id)?.nickname
          } / ${instrument.name}`,
      ),
      "ui:disabled": !instruments?.length,
    },
    observed_by: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    observer_point_of_contact: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    reduced_by: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    reducer_point_of_contact: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    pi: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    pi_point_of_contact: {
      "ui:enumNames": userEnumOptions?.enumNames,
    },
    "ui:order": [
      "*",
      "observer_mode",
      "observer_point_of_contact",
      "observed_by",
      "reducer_mode",
      "reducer_point_of_contact",
      "reduced_by",
      "pi_mode",
      "pi_point_of_contact",
      "pi",
      "wave_column",
      "flux_column",
      "has_fluxerr",
      "fluxerr_column",
      "user_label",
    ],
  };

  const parseAscii = ({ formData }) => {
    dispatch({ type: spectraActions.RESET_PARSED_SPECTRUM });
    const parsed_spectrum = dataUriToBuffer(formData.file);
    const ascii = new TextDecoder().decode(parsed_spectrum.buffer);
    const payload = {
      ascii,
      flux_column: formData.flux_column,
      wave_column: formData.wave_column,
      fluxerr_column:
        formData?.has_fluxerr === "Yes" ? formData.fluxerr_column : null,
    };
    dispatch(spectraActions.parseASCIISpectrum(payload));
  };

  const uploadSpectrum = async () => {
    if (!parsed) {
      dispatch(showNotification("No spectrum loaded on frontend.", "error"));
    }
    const parsed_form = dataUriToBuffer(persistentFormData.file);
    const ascii = new TextDecoder().decode(parsed_form.buffer);
    const filename = persistentFormData.file.split(";")[1].split("name=")[1];
    const payload = {
      ascii,
      flux_column: persistentFormData.flux_column,
      wave_column: persistentFormData.wave_column,
      fluxerr_column:
        persistentFormData?.has_fluxerr === "Yes"
          ? persistentFormData.fluxerr_column
          : null,
      obj_id: route.id,
      instrument_id: persistentFormData.instrument_id,
      type: persistentFormData.spectrum_type,
      label: persistentFormData.user_label,
      // 40_587 is the MJD of the unix epoch, 86400 converts days to seconds.
      observed_at: dayjs
        .unix((persistentFormData.mjd - 40_587) * 86400)
        .utc()
        .format(),
      filename,
      // The observed_by list of users is either the actual users
      // who are observers, or users to be listed as points of
      // contact
      observed_by:
        persistentFormData?.observer_mode === "User"
          ? persistentFormData.observed_by
          : persistentFormData.observer_point_of_contact,
      // If providing external observers as free text, the text
      // will be in the 'observed_by' field and the associated
      // users will be in 'observer_point_of_contact'
      external_observer:
        persistentFormData?.observer_mode === "External"
          ? persistentFormData.observed_by
          : null,
      // The reduced_by list of users is either the actual users
      // who are reducers, or users to be listed as points of
      // contact
      reduced_by:
        persistentFormData?.reducer_mode === "User"
          ? persistentFormData.reduced_by
          : persistentFormData.reducer_point_of_contact,
      // If providing external reducers as free text, the text
      // will be in the 'reduced_by' field and the associated
      // users will be in 'reducer_point_of_contact'
      external_reducer:
        persistentFormData?.reducer_mode === "External"
          ? persistentFormData.reduced_by
          : null,
      pi:
        persistentFormData?.pi_mode === "User"
          ? persistentFormData.pi
          : persistentFormData.pi_point_of_contact,
      external_pi:
        persistentFormData?.pi_mode === "External"
          ? persistentFormData.pi
          : null,
      group_ids: persistentFormData.group_ids,
    };
    const result = await dispatch(spectraActions.uploadASCIISpectrum(payload));
    if (result.status === "success") {
      dispatch(showNotification("Upload successful."));
      dispatch({ type: spectraActions.RESET_PARSED_SPECTRUM });
      setPersistentFormData({
        file: undefined,
        group_ids: source.groups?.map((group) => group.id),
        mjd: undefined,
        wave_column: 0,
        flux_column: 1,
        has_fluxerr: "No",
        instrument_id: undefined,
        spectrum_type: "source",
        user_label: undefined,
        fluxerr_column: undefined,
        observed_by: undefined,
        reduced_by: undefined,
      });
      setFormKey(Date.now());
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={4} sm={12}>
        <Paper sx={{ position: "relative" }}>
          <Typography variant="h6">
            Upload Spectrum ASCII File for&nbsp;
            <Link to={`/source/${route.id}`}>{route.id}</Link>
          </Typography>
          <Box sx={{ position: "absolute", top: 2, right: 3 }}>
            <Tooltip
              title={
                <Typography variant="body2">
                  Use this form to upload ASCII spectrum files to SkyPortal. For
                  details on allowed file formatting, see the&nbsp;
                  <Link
                    to="https://skyportal.io/docs/api#/paths/~1api~1spectrum~1parse~1ascii/post"
                    target="_blank"
                    rel="noreferrer"
                  >
                    SkyPortal API docs.
                  </Link>
                </Typography>
              }
            >
              <HelpOutlineIcon sx={{ fontSize: 20, color: "gray" }} />
            </Tooltip>
          </Box>
          {uploadedFromURL && (
            <Typography
              variant="body1"
              color="textSecondary"
              fontStyle="italic"
            >
              <b>
                Form prefilled from URL parameters (the ascii file was
                downloaded, no need to upload manually).
              </b>
            </Typography>
          )}
          <Form
            schema={uploadFormSchema}
            uiSchema={uiSchema}
            validator={validator}
            onSubmit={parseAscii}
            formData={persistentFormData}
            onChange={({ formData }) => {
              if (formData.file !== persistentFormData.file) {
                setFormKey(Date.now());
                dispatch({ type: spectraActions.RESET_PARSED_SPECTRUM });
                setUploadedFromURL(false);
              }
              setPersistentFormData(formData);
            }}
            key={formKey}
          >
            <Button
              secondary
              endIcon={<VisibilityIcon />}
              type="submit"
              sx={{
                position: "sticky",
                bottom: 16,
                left: "50%",
                transform: "translateX(-58%)",
                boxShadow: 2,
              }}
            >
              Preview Spectrum
            </Button>
          </Form>
        </Paper>
      </Grid>
      {parsed && (
        <Grid item md={8} sm={12}>
          <Paper>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="h6">Spectrum Preview</Typography>
              <Button primary onClick={uploadSpectrum}>
                Upload Spectrum
              </Button>
            </Box>
            <Suspense fallback={<CircularProgress />}>
              <SpectrumPreview data={data} />
            </Suspense>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Metadata</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <MUIDataTable
                  columns={header_columns}
                  data={header}
                  options={{ selectableRows: "none", elevation: 0 }}
                />
              </AccordionDetails>
            </Accordion>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Spectrum Table</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <MUIDataTable
                  columns={data_columns}
                  data={data}
                  options={{ selectableRows: "none", elevation: 0 }}
                />
              </AccordionDetails>
            </Accordion>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

UploadSpectrumForm.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(UploadSpectrumForm);
