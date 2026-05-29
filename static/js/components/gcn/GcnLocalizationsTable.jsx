import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Chip from "@mui/material/Chip";
import { makeStyles } from "tss-react/mui";
import DeleteIcon from "@mui/icons-material/Delete";

import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { dec_to_dms, ra_to_hours } from "../../units";
import * as localizationActions from "../../ducks/localization";

const useStyles = makeStyles()(() => ({
  accordion: {
    width: "100%",
  },
  container: {
    margin: "0rem 0",
    width: "100%",
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

const GcnLocalizationsTable = ({ localizations }) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [localizationToDelete, setLocalizationToDelete] = useState(null);
  const openDialog = (dateobs, name) => {
    setDialogOpen(true);
    setLocalizationToDelete({ dateobs, name });
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setLocalizationToDelete(null);
  };

  const deleteLocalization = () => {
    dispatch(
      localizationActions.deleteLocalization(
        localizationToDelete.dateobs,
        localizationToDelete.name,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Localization deleted"));
        closeDialog();
      }
    });
  };

  if (!localizations || localizations.length === 0) {
    return <p>No localizations for this event...</p>;
  }
  let propertyNames = [];
  if (localizations.length > 0) {
    (localizations || []).forEach((loc) => {
      if (loc?.properties?.length > 0) {
        if (loc.properties[0].data) {
          // append the keys of the properties object to the propertyNames array
          propertyNames = propertyNames.concat(
            Object.keys(loc.properties[0].data),
          );
        }
      }
    });
  }

  const uniquePropertyNames = [...new Set(propertyNames)];

  const propertiesWithUniqueKeys = localizations.map((loc) => {
    const newProperty = {
      ...loc,
    };
    if (loc?.properties?.length > 0) {
      uniquePropertyNames.forEach((name) => {
        if (Object.keys(loc.properties[0].data).includes(name)) {
          if (typeof loc.properties[0].data[name] === "number") {
            if (
              loc.properties[0].data[name] > 10000 ||
              loc.properties[0].data[name] < -10000
            ) {
              newProperty[name] = loc.properties[0].data[name].toExponential(4);
            } else if (
              loc.properties[0].data[name] > 0.0001 ||
              loc.properties[0].data[name] < -0.0001
            ) {
              newProperty[name] = loc.properties[0].data[name].toFixed(4);
            } else if (loc.properties[0].data[name] === 0) {
              newProperty[name] = 0;
            } else {
              newProperty[name] = loc.properties[0].data[name].toExponential(4);
            }
          } else {
            newProperty[name] = loc.properties[0].data[name];
          }
        } else {
          newProperty[name] = null;
        }
      });
    } else {
      uniquePropertyNames.forEach((name) => {
        newProperty[name] = null;
      });
    }
    return newProperty;
  });

  const renderName = (params) => {
    const localization = params.row;
    return (
      <div>
        <Button
          secondary
          href={`/api/localization/${localization.dateobs}/name/${localization.localization_name}/download`}
          download={`${localization.dateobs.replaceAll(":", "-")}_${
            localization.localization_name
          }.fits`}
          size="small"
          type="submit"
          data-testid={`localization_${localization.id}`}
        >
          {localization.localization_name}
        </Button>
      </div>
    );
  };

  const renderCenter = (params) => {
    const localization = params.row;
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

  const renderTags = (params) => {
    const localization = params.row;
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

  const renderDelete = (params) => {
    const localization = params.row;
    return (
      <div>
        <Button
          id="delete_button"
          classes={{
            root: classes.localizationDelete,
          }}
          onClick={() =>
            openDialog(localization.dateobs, localization.localization_name)
          }
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteLocalization}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="localization"
        />
      </div>
    );
  };

  const columns = [
    { field: "created_at", headerName: "Created at", flex: 1, minWidth: 160 },
    {
      field: "localization_name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderName,
    },
    {
      field: "Center",
      headerName: "Center",
      flex: 2,
      minWidth: 280,
      sortable: false,
      renderCell: renderCenter,
    },
    {
      field: "Tags",
      headerName: "Tags",
      flex: 1,
      minWidth: 120,
      sortable: false,
      renderCell: renderTags,
    },
    ...uniquePropertyNames.map((name) => ({
      field: name,
      headerName: name,
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (value, row) => row[name],
    })),
    {
      field: "delete",
      headerName: " ",
      width: 70,
      sortable: false,
      renderCell: renderDelete,
    },
  ];

  return (
    <div className={classes.container}>
      <StyledDataGrid
        autoHeight
        rows={propertiesWithUniqueKeys}
        columns={columns}
        getRowId={(row) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[1, 10, 15]}
        showToolbar
      />
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
        }),
      ),
      tags: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          text: PropTypes.string.isRequired,
        }),
      ),
      center: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    }),
  ).isRequired,
};

export default GcnLocalizationsTable;
