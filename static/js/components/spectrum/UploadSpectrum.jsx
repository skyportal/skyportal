import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link, useSearchParams } from "react-router-dom";
import MUIDataTable from "mui-datatables";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv6";
import dataUriToBuffer from "data-uri-to-buffer";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import embed from "vega-embed";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { showNotification } from "baselayer/components/Notifications";

import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Button from "../Button";

import { HtmlTooltip } from "../photometry/UploadPhotometry";
import withRouter from "../withRouter";

import * as spectraActions from "../../ducks/spectra";
import { fetchSource } from "../../ducks/source";
import { fetchUsers } from "../../ducks/users";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  formBox: {
    padding: "1rem",
  },
  vegaDiv: {
    width: "100%",
  },
  displayBlock: {
    display: "block",
  },
  accordion: {
    margin: "1rem",
  },
  dataTable: {
    width: "100%",
  },
  alignRight: {
    position: "absolute",
    right: "0px",
    bottom: "0px",
  },
  bottomRow: {
    position: "relative",
  },
  submitButton: {
    display: "inline-block",
  },
}));

const spectrumPreviewSpec = (data) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v5.2.0.json",
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

const SpectrumPreview = React.memo((props) => {
  const { data } = props;
  const classes = useStyles();
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spectrumPreviewSpec(data), {
            actions: false,
          });
        }
      }}
      className={classes.vegaDiv}
    />
  );
});

SpectrumPreview.displayName = "SpectrumPreview";
SpectrumPreview.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      wavelength: PropTypes.number.isRequired,
      flux: PropTypes.number.isRequired,
      error: PropTypes.number,
    }),
  ).isRequired,
};

const UploadSpectrumForm = ({ route }) => {
  const { parsed } = useSelector((state) => state.spectra);
  const groups = useSelector((state) => state.groups.all);
  const { users } = useSelector((state) => state.users);
  const instrumentList = useSelector(
    (state) => state.instruments.instrumentList,
  );
  const telescopes = useSelector((state) => state.telescopes.telescopeList);
  const source = useSelector((state) => state.source);
  const dispatch = useDispatch();
  const classes = useStyles();
  const [persistentFormData, setPersistentFormData] = useState({});
  const [formKey, setFormKey] = useState(null);
  const spectrumTypes = useSelector(
    (state) => state.config.allowedSpectrumTypes,
  );

  const defaultSpectrumType = useSelector(
    (state) => state.config.defaultSpectrumType,
  );

  const [searchParams] = useSearchParams();

  const [uploadedFromURL, setUploadedFromURL] = useState(false);

  // on page load or refresh, block until state.spectra.parsed is reset
  useEffect(() => {
    const blockingFunc = async () => {
      dispatch({ type: spectraActions.RESET_PARSED_SPECTRUM });
      dispatch(fetchUsers());
      const result = await dispatch(fetchSource(route.id));

      let file_url = searchParams.get("file_url");
      if (file_url && file_url.startsWith('"') && file_url.endsWith('"')) {
        file_url = file_url.slice(1, -1);
      }
      let file_name = searchParams.get("file_name");
      if (file_name && file_name.startsWith('"') && file_name.endsWith('"')) {
        file_name = file_name.slice(1, -1);
      }

      let file;
      if (file_url) {
        const response = await fetch(file_url);
        const blob = await response.blob();
        // we want to set file to a data url, so we can pass it to the form
        file = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            resolve(reader.result);
          };
          reader.readAsDataURL(blob);
        });
        if (!file.includes("name=")) {
          const file_type = file.split(";")[0].split(":")[1];
          file = file.replace(file_type, `${file_type};name=${file_name}`);
        }
        setUploadedFromURL(true);
      }

      const defaultFormData = {
        file,
        group_ids: searchParams.get("group_ids")
          ? searchParams
              .get("group_ids")
              .split(",")
              .map((id) => parseInt(id, 10))
          : result.data.groups?.map((group) => group.id),
        mjd: searchParams.get("mjd")
          ? parseFloat(searchParams.get("mjd"))
          : undefined,
        wave_column: searchParams.get("wave_column")
          ? parseInt(searchParams.get("wave_column"), 10)
          : 0,
        flux_column: searchParams.get("flux_column")
          ? parseInt(searchParams.get("flux_column"), 10)
          : 1,
        has_fluxerr: searchParams.get("has_fluxerr") || "No",
        instrument_id: searchParams.get("instrument_id")
          ? parseInt(searchParams.get("instrument_id"), 10)
          : undefined,
        spectrum_type: searchParams.get("spectrum_type") || "source",
        user_label: searchParams.get("user_label") || undefined,
        fluxerr_column: searchParams.get("fluxerr_column")
          ? parseInt(searchParams.get("fluxerr_column"), 10)
          : undefined,
        observed_by: searchParams.get("observed_by")
          ? searchParams
              .get("observed_by")
              .split(",")
              .map((id) => parseInt(id, 10))
          : undefined,
        reduced_by: searchParams.get("reduced_by")
          ? searchParams
              .get("reduced_by")
              .split(",")
              .map((id) => parseInt(id, 10))
          : undefined,
      };

      setPersistentFormData(defaultFormData);
    };
    blockingFunc();
  }, [dispatch, route.id, searchParams]);

  if (
    !groups ||
    !instrumentList ||
    !telescopes ||
    users.length === 0 ||
    source.id !== route.id
  ) {
    return (
      <p>
        <CircularProgress color="secondary" />
      </p>
    );
  }

  const instruments = instrumentList.filter((inst) =>
    inst.type.includes("spec"),
  );

  const newPersistentFormData = { ...persistentFormData };
  newPersistentFormData.group_ids = source.groups?.map((group) => group.id);

  const header = [];
  const data = [];
  let headerHasComments = false;
  if (parsed) {
    if (parsed.altdata) {
      Object.entries(parsed.altdata).forEach(([key, value]) => {
        if (typeof value === "object" && !(value == null)) {
          headerHasComments = true;
          header.push({ key, value: value.value, comment: value.comment });
        } else {
          header.push({ key, value });
        }
      });
      if (headerHasComments) {
        header.forEach((obj) => {
          if (!("comment" in obj)) {
            obj.comment = null;
          }
        });
      }
    }
    parsed.wavelengths.forEach((w, i) => {
      const flux = parsed.fluxes[i];
      const fluxerr = parsed.errors ? parsed.errors[i] : null;
      const datum = { flux, wavelength: w };
      if (fluxerr) {
        datum.error = fluxerr;
      }
      data.push(datum);
    });
  }

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
  ];

  if (headerHasComments) {
    header_columns.push({
      name: "comment",
      label: "Comment",
      options: {
        filter: false,
        sort: true,
      },
    });
  }

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
  ];

  if (parsed && "errors" in parsed) {
    data_columns.push({
      name: "error",
      label: "Error",
      options: {
        filter: false,
        sort: true,
      },
    });
  }

  const getUserDisplay = (user) => {
    const lastOrFirst = user?.first_name || user?.last_name;
    const displayStr = `${user.username} ${lastOrFirst ? "(" : ""}${
      user?.first_name ? user.first_name : ""
    } ${user?.last_name ? user.last_name : ""}${lastOrFirst ? ")" : ""}`;
    return displayStr;
  };

  const uploadFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Spectrum file",
      },
      group_ids: {
        type: "array",
        title: "Share with...",
        items: {
          type: "integer",
          anyOf: groups?.map((group) => ({
            enum: [group.id],
            title: group.name,
          })),
        },
        uniqueItems: true,
      },
      pi_mode: {
        type: "string",
        default: "User",
        title: "PI type",
        enum: ["User", "External"],
      },
      pi: {
        type: "array",
        title: "PI(s)",
        items: {
          type: "integer",
          anyOf: users?.map((user) => ({
            enum: [user.id],
            title: getUserDisplay(user),
          })),
        },
        uniqueItems: true,
      },
      reducer_mode: {
        type: "string",
        default: "User",
        title: "Reducer type",
        enum: ["User", "External"],
      },
      reduced_by: {
        type: "array",
        title: "Reducers",
        items: {
          type: "integer",
          anyOf: users?.map((user) => ({
            enum: [user.id],
            title: getUserDisplay(user),
          })),
        },
        uniqueItems: true,
      },
      observer_mode: {
        type: "string",
        default: "User",
        title: "Observer type",
        enum: ["User", "External"],
      },
      observed_by: {
        type: "array",
        title: "Observers",
        items: {
          type: "integer",
          anyOf: users?.map((user) => ({
            enum: [user.id],
            title: getUserDisplay(user),
          })),
        },
        uniqueItems: true,
      },
      mjd: {
        type: "number",
        title: "Observation MJD",
      },
      instrument_id: {
        type: "integer",
        title: "Instrument",
        anyOf: instruments?.map((instrument) => ({
          enum: [instrument.id],
          type: "integer",
          title: `${
            telescopes.find((t) => t.id === instrument.telescope_id)?.nickname
          } / ${instrument.name}`,
        })),
      },
      spectrum_type: {
        type: "string",
        default: defaultSpectrumType,
        title: "Spectrum type",
        enum: spectrumTypes,
      },
      user_label: {
        type: "string",
        title: "User label",
        default: "",
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
                  anyOf: users?.map((user) => ({
                    enum: [user.id],
                    title: getUserDisplay(user),
                  })),
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
    "ui:order": [
      "group_ids",
      "file",
      "mjd",
      "instrument_id",
      "spectrum_type",
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
    const ascii = dataUriToBuffer(formData.file).toString();
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
      throw new Error("No spectrum loaded on frontend.");
    }
    const ascii = dataUriToBuffer(persistentFormData.file).toString();
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
        <Paper className={classes.formBox}>
          <Typography variant="h6">
            Upload Spectrum ASCII File for&nbsp;
            <Link to={`/source/${route.id}`}>{route.id}</Link>
          </Typography>
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
            noHtml5Validation
            key={formKey}
          >
            <div className={classes.bottomRow}>
              <Button secondary type="submit" className={classes.submitButton}>
                Preview
              </Button>
              <HtmlTooltip
                title={
                  <p>
                    Use this form to upload ASCII spectrum files to SkyPortal.
                    For details on allowed file formatting, see the&nbsp;
                    <a href="http://skyportal.io/docs/api#/paths/~1api~1spectrum~1parse~1ascii/post">
                      SkyPortal API docs.
                    </a>
                  </p>
                }
                className={classes.alignRight}
              >
                <HelpOutlineIcon />
              </HtmlTooltip>
            </div>
          </Form>
        </Paper>
      </Grid>
      {parsed && (
        <Grid item md={8} sm={12}>
          <Paper className={classes.formBox}>
            <Typography variant="h6">Spectrum Preview</Typography>
            <div className={classes.vegaDiv}>
              <Suspense fallback={<CircularProgress color="secondary" />}>
                <SpectrumPreview data={data} />
              </Suspense>
            </div>
            <Accordion className={classes.accordion}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Metadata</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <MUIDataTable
                  className={classes.dataTable}
                  columns={header_columns}
                  data={header}
                  options={{ selectableRows: "none", elevation: 0 }}
                />
              </AccordionDetails>
            </Accordion>
            <Accordion className={classes.accordion}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Spectrum Table</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <MUIDataTable
                  className={classes.dataTable}
                  columns={data_columns}
                  data={data}
                  options={{ selectableRows: "none", elevation: 0 }}
                />
              </AccordionDetails>
            </Accordion>
            <div className={classes.bottomRow}>
              <Button secondary onClick={uploadSpectrum}>
                Upload Spectrum
              </Button>
            </div>
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
