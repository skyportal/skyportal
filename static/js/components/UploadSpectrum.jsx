import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import MUIDataTable from "mui-datatables";
import Form from "@rjsf/material-ui";
import dataUriToBuffer from "data-uri-to-buffer";
import Typography from "@material-ui/core/Typography";
import Accordion from "@material-ui/core/Accordion";
import Grid from "@material-ui/core/Grid";
import Paper from "@material-ui/core/Paper";
import Button from "@material-ui/core/Button";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import { makeStyles } from "@material-ui/core/styles";
import embed from "vega-embed";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { showNotification } from "baselayer/components/Notifications";

import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";

import { HtmlTooltip } from "./UploadPhotometry";

import * as Actions from "../ducks/spectra";
import { fetchSource } from "../ducks/source";
import { fetchUsers } from "../ducks/users";
import { RESET_PARSED_SPECTRUM } from "../ducks/spectra";

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
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
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
    })
  ).isRequired,
};

const UploadSpectrumForm = ({ route }) => {
  const { parsed } = useSelector((state) => state.spectra);
  const groups = useSelector((state) => state.groups.all);
  const users = useSelector((state) => state.users.allUsers);
  const instrumentList = useSelector(
    (state) => state.instruments.instrumentList
  );
  const telescopes = useSelector((state) => state.telescopes.telescopeList);
  const source = useSelector((state) => state.source);
  const dispatch = useDispatch();
  const classes = useStyles();
  const [persistentFormData, setPersistentFormData] = useState({});
  const [formKey, setFormKey] = useState(null);

  // on page load or refresh, block until state.spectra.parsed is reset
  useEffect(() => {
    const blockingFunc = async () => {
      dispatch({ type: Actions.RESET_PARSED_SPECTRUM });
      dispatch(fetchUsers());
      const result = await dispatch(fetchSource(route.id));
      const defaultFormData = {
        file: undefined,
        group_ids: result.data.groups.map((group) => group.id),
        mjd: undefined,
        wave_column: 0,
        flux_column: 1,
        has_fluxerr: "No",
        instrument_id: undefined,
        fluxerr_column: undefined,
        observed_by: undefined,
        reduced_by: undefined,
      };
      setPersistentFormData(defaultFormData);
    };
    blockingFunc();
  }, [dispatch, route.id]);

  if (
    !groups ||
    !instrumentList ||
    !telescopes ||
    users.length === 0 ||
    source.id !== route.id
  ) {
    return <p>Loading...</p>;
  }

  const instruments = instrumentList.filter((inst) =>
    inst.type.includes("spec")
  );

  const newPersistentFormData = { ...persistentFormData };
  newPersistentFormData.group_ids = source.groups.map((group) => group.id);

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
          anyOf: groups.map((group) => ({
            enum: [group.id],
            title: group.name,
          })),
        },
        uniqueItems: true,
      },
      reduced_by: {
        type: "array",
        title: "Reducers",
        items: {
          type: "integer",
          anyOf: users.map((user) => ({
            enum: [user.id],
            title: user.username,
          })),
        },
        uniqueItems: true,
      },
      observed_by: {
        type: "array",
        title: "Observers",
        items: {
          type: "integer",
          anyOf: users.map((user) => ({
            enum: [user.id],
            title: user.username,
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
        enum: instruments.map((instrument) => instrument.id),
        enumNames: instruments.map((instrument) => {
          const telescope = telescopes.find(
            (t) => t.id === instrument.telescope_id
          );
          let name = "";
          if (telescope) {
            name += `${telescope.nickname} / `;
          }
          name += instrument.name;
          return name;
        }),
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
      "has_fluxerr",
      "mjd",
      "wave_column",
      "flux_column",
      "instrument_id",
    ],
    dependencies: {
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

  const parseAscii = ({ formData }) => {
    dispatch({ type: Actions.RESET_PARSED_SPECTRUM });
    const ascii = dataUriToBuffer(formData.file).toString();
    const payload = {
      ascii,
      flux_column: formData.flux_column,
      wave_column: formData.wave_column,
      fluxerr_column:
        formData?.has_fluxerr === "Yes" ? formData.fluxerr_column : null,
    };
    dispatch(Actions.parseASCIISpectrum(payload));
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
      // 40_587 is the MJD of the unix epoch, 86400 converts days to seconds.
      observed_at: dayjs
        .unix((persistentFormData.mjd - 40_587) * 86400)
        .utc()
        .format(),
      filename,
      observed_by: persistentFormData.observed_by,
      reduced_by: persistentFormData.reduced_by,
    };
    const result = await dispatch(Actions.uploadASCIISpectrum(payload));
    if (result.status === "success") {
      dispatch(showNotification("Upload successful."));
      dispatch({ type: RESET_PARSED_SPECTRUM });
      setPersistentFormData({
        file: undefined,
        group_ids: source.groups.map((group) => group.id),
        mjd: undefined,
        wave_column: 0,
        flux_column: 1,
        has_fluxerr: "No",
        instrument_id: undefined,
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
          <Form
            schema={uploadFormSchema}
            onSubmit={parseAscii}
            formData={persistentFormData}
            onChange={({ formData }) => {
              if (formData.file !== persistentFormData.file) {
                setFormKey(Date.now());
                dispatch({ type: RESET_PARSED_SPECTRUM });
              }
              setPersistentFormData(formData);
            }}
            noHtml5Validation
            key={formKey}
          >
            <div className={classes.bottomRow}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                className={classes.submitButton}
              >
                Preview
              </Button>
              <HtmlTooltip
                interactive
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
              <Suspense fallback="Loading spectrum plot...">
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
              <Button
                onClick={uploadSpectrum}
                variant="contained"
                color="primary"
              >
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

export default UploadSpectrumForm;
