import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { dec_to_dms, ra_to_hours } from "../../units";
import { useDeleteLocalizationMutation } from "../../ducks/localization";

interface GcnLocalizationsTableProps {
  localizations: any[];
}

const GcnLocalizationsTable = ({
  localizations,
}: GcnLocalizationsTableProps) => {
  const dispatch = useAppDispatch();
  const [deleteLocalizationMutation] = useDeleteLocalizationMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [localizationToDelete, setLocalizationToDelete] = useState<any>(null);
  const openDialog = (dateobs: any, name: any) => {
    setDialogOpen(true);
    setLocalizationToDelete({ dateobs, name });
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setLocalizationToDelete(null);
  };

  const deleteLocalization = async () => {
    try {
      await deleteLocalizationMutation({
        dateobs: localizationToDelete.dateobs,
        localization_name: localizationToDelete.name,
      }).unwrap();
      dispatch(showNotification("Localization deleted"));
      closeDialog();
    } catch {
      // error notification handled by the baseQuery
    }
  };

  if (!localizations || localizations.length === 0) {
    return (
      <Typography variant="body2">
        No localizations for this event...
      </Typography>
    );
  }
  let propertyNames: string[] = [];
  if (localizations.length > 0) {
    (localizations || []).forEach((loc) => {
      if (loc?.properties?.length > 0) {
        if (loc.properties[0].data) {
          propertyNames = propertyNames.concat(
            Object.keys(loc.properties[0].data),
          );
        }
      }
    });
  }

  const uniquePropertyNames = [...new Set(propertyNames)];

  const propertiesWithUniqueKeys = localizations.map((loc) => {
    const newProperty: Record<string, any> = {
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

  const renderName = (params: any) => {
    const localization = params.row;
    return (
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
    );
  };

  const renderCenter = (params: any) => {
    const center = params.row?.center;
    return (
      <Box
        sx={{
          display: "flex",
          flexFlow: "row wrap",
          alignItems: "center",
          py: 0.25,
        }}
      >
        <Box component="span">
          <b>Position (J2000):&nbsp; &nbsp;</b>
          <Box component="span" sx={{ fontWeight: "bold", fontSize: "110%" }}>
            {ra_to_hours(center.ra, ":")} &nbsp;
            {dec_to_dms(center.dec, ":")} &nbsp;
          </Box>
        </Box>
        <Box component="span">
          (&alpha;,&delta;= {center.ra}, &nbsp;
          {center.dec}; &nbsp;
          <i>l</i>,<i>b</i>={center.gal_lon.toFixed(6)}, &nbsp;
          {center.gal_lat.toFixed(6)})
          {center.ebv ? (
            <>
              <i> E(B-V)</i>={center.ebv.toFixed(2)}
            </>
          ) : null}
        </Box>
      </Box>
    );
  };

  const renderTags = (params: any) => {
    const tags = [
      ...new Set<string>(params.row.tags?.map((tag: any) => tag.text) || []),
    ];
    return tags.map((tag) => <Chip size="small" label={tag} key={tag} />);
  };

  const renderDelete = (params: any) => {
    const localization = params.row;
    return (
      <Button
        id="delete_button"
        onClick={() =>
          openDialog(localization.dateobs, localization.localization_name)
        }
      >
        <DeleteIcon />
      </Button>
    );
  };

  const columns: any[] = [
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
      valueGetter: (_value: any, row: any) => row[name],
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
    <>
      <StyledDataGrid
        autoHeight
        rows={propertiesWithUniqueKeys}
        columns={columns}
        getRowId={(row: any) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[1, 10, 15]}
        slots={{ toolbar: DataGridToolbar }}
        slotProps={{ toolbar: { title: "Localization Properties" } }}
        showToolbar
      />
      <ConfirmDeletionDialog
        deleteFunction={deleteLocalization}
        dialogOpen={dialogOpen}
        closeDialog={closeDialog}
        resourceName="localization"
      />
    </>
  );
};

export default GcnLocalizationsTable;
