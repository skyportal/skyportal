import React, { Suspense, useEffect } from "react";
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
import { makeStyles } from "@material-ui/core/styles";
import embed from "vega-embed";

import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";

import * as Actions from "../ducks/spectra";

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
}));

const spectrumPreviewSpec = (data) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width: "container",
  height: 200,
  data: { values: data },
  mark: "line",
  encoding: {
    x: { field: "wavelength", type: "quantitative" },
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
  const dispatch = useDispatch();
  const classes = useStyles();

  // on page load or refresh, block until state.spectra.parsed is reset
  useEffect(() => {
    dispatch({ type: Actions.RESET_PARSED_SPECTRUM });
  }, [dispatch]);

  const header = [];
  const data = [];
  let headerHasComments = false;
  if (parsed) {
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
      wave_column: {
        type: "integer",
        default: 0,
      },
      flux_column: {
        type: "integer",
        default: 1,
      },
      fluxerr_column: {
        type: "integer",
        default: null,
      },
    },
    required: ["file"],
  };

  const parseAscii = ({ formData }) => {
    const ascii = dataUriToBuffer(formData.file).toString();
    const payload = {
      ascii,
      flux_column: formData.flux_column,
      wave_column: formData.wave_column,
      fluxerr_column: formData.fluxerr_column,
    };
    dispatch(Actions.parseASCIISpectrum(payload));
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={4} sm={12}>
        <Paper className={classes.formBox}>
          <Typography variant="h6">
            Upload Spectrum ASCII File for&nbsp;
            <Link to={`/source/${route.id}`}>{route.id}</Link>
          </Typography>
          <Form schema={uploadFormSchema} onSubmit={parseAscii} />
        </Paper>
      </Grid>

      {parsed && (
        <Grid item md={8} sm={12}>
          <Paper className={classes.formBox}>
            <Typography variant="h6">Spectrum Preview</Typography>
            <Suspense fallback="Loading spectrum plot...">
              <div className={classes.vegaDiv}>
                <SpectrumPreview data={data} />
              </div>
            </Suspense>
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
