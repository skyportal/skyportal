import React from "react";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

import Button from "./Button";
import { ra_to_hours, dec_to_dms } from "../units";

const useStyles = makeStyles(() => ({
  accordion: {
    width: "100%",
  },
  container: {
    margin: "0rem 0",
  },
  position: {
    fontWeight: "bold",
    fontSize: "110%",
  },
  sourceInfo: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  infoLine: {
    // Get it's own line
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    padding: "0.25rem 0",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
      palette: theme.palette,
      overrides: {
        MUIDataTable: {
          paper: {
            width: "100%",
          },
        },
        MUIDataTableBodyCell: {
          stackedCommon: {
            overflow: "hidden",
            "&:last-child": {
              paddingLeft: "0.25rem",
            },
          },
        },
        MUIDataTablePagination: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    })
  );

const GcnLocalizationsTable = ({ localizations }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!localizations || localizations.length === 0) {
    return <p>No localizations for this event...</p>;
  }

  const getDataTableColumns = () => {
    const columns = [{ name: "created_at", label: "Created at" }];

    const renderName = (dataIndex) => {
      const localization = localizations[dataIndex];
      return (
        <div>
          <Button
            secondary
            href={`/api/localization/${localization.dateobs}/name/${localization.localization_name}/download`}
            download={`localization-${localization.id}.fits`}
            size="small"
            type="submit"
            data-testid={`localization_${localization.id}`}
          >
            {localization.localization_name}
          </Button>
        </div>
      );
    };
    columns.push({
      name: "localization_name",
      label: "Name",
      options: {
        customBodyRenderLite: renderName,
      },
    });

    const renderCenter = (dataIndex) => {
      const localization = localizations[dataIndex];
      const center = localization?.center;

      return (
        <div className={classes.infoLine}>
          <div className={classes.sourceInfo}>
            <div>
              <b>Position (J2000):&nbsp; &nbsp;</b>
            </div>
            <div>
              <span className={classes.position}>
                {ra_to_hours(center.ra, ":")} &nbsp;
                {dec_to_dms(center.dec, ":")} &nbsp;
              </span>
            </div>
          </div>
          <div className={classes.sourceInfo}>
            <div>
              (&alpha;,&delta;= {center.ra}, &nbsp;
              {center.dec}; &nbsp;
            </div>
            <div>
              <i>l</i>,<i>b</i>={center.gal_lon.toFixed(6)}, &nbsp;
              {center.gal_lat.toFixed(6)})
            </div>
            {center.ebv ? (
              <div>
                <i> E(B-V)</i>={center.ebv.toFixed(2)}
              </div>
            ) : null}
          </div>
        </div>
      );
    };
    columns.push({
      name: "Center",
      label: "Center",
      options: {
        customBodyRenderLite: renderCenter,
      },
    });

    const renderTags = (dataIndex) => {
      const localization = localizations[dataIndex];

      const localizationTags = [];
      localization.tags?.forEach((tag) => {
        localizationTags.push(tag.text);
      });
      const localizationTagsUnique = [...new Set(localizationTags)];

      return (
        <div>
          {localizationTagsUnique.map((tag) => (
            <Chip size="small" label={tag} key={tag} />
          ))}
        </div>
      );
    };

    columns.push({
      name: "Tags",
      label: "Tags",
      options: {
        customBodyRenderLite: renderTags,
      },
    });

    const renderProperties = (dataIndex) => {
      const localization = localizations[dataIndex];
      const properties = localization?.properties;

      return (
        <div>
          {properties.length > 0
            ? JSON.stringify(localization.properties[0].data)
            : ""}
        </div>
      );
    };
    columns.push({
      name: "Properties",
      label: "Properties",
      options: {
        customBodyRenderLite: renderProperties,
      },
    });

    return columns;
  };

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
  };

  return (
    <div className={classes.container}>
      <Accordion className={classes.accordion} key="localizations_table_div">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="gcn-localizations"
          data-testid="gcn-localizations-header"
        >
          <Typography variant="subtitle1">Property Lists</Typography>
        </AccordionSummary>
        <AccordionDetails data-testid="gcn-localizations-Table">
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={localizations}
                options={options}
                columns={getDataTableColumns()}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </AccordionDetails>
      </Accordion>
    </div>
  );
};

GcnLocalizationsTable.propTypes = {
  localizations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      localization_name: PropTypes.string,
      dateobs: PropTypes.string,
      properties: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
        })
      ),
      tags: PropTypes.arrayOf(PropTypes.string),
      center: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    })
  ).isRequired,
};

export default GcnLocalizationsTable;
