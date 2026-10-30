import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { dec_to_dms, ra_to_hours } from "../../units";
import { useDeleteLocalizationMutation } from "../../ducks/localization";

dayjs.extend(utc);

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

  const renderName = ({ row }: any) => (
    <Link
      href={`/api/localization/${row.dateobs}/name/${row.localization_name}/download`}
      download={`${row.dateobs.replaceAll(":", "-")}_${row.localization_name}.fits`}
      underline="hover"
      data-testid={`localization_${row.id}`}
      sx={{ wordBreak: "break-all" }}
    >
      {row.localization_name}
    </Link>
  );

  const renderCenter = ({ row }: any) => {
    const { center } = row;
    return (
      <Box>
        <Typography variant="body2">
          {ra_to_hours(center.ra, ":")} {dec_to_dms(center.dec, ":")}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          α, δ = {center.ra.toFixed(5)}, {center.dec.toFixed(5)} · l, b ={" "}
          {center.gal_lon.toFixed(5)}, {center.gal_lat.toFixed(5)}
          {center.ebv ? ` · E(B-V) = ${center.ebv.toFixed(2)}` : ""}
        </Typography>
      </Box>
    );
  };

  const renderTags = (params: any) => {
    const tags = [
      ...new Set<string>(params.row.tags?.map((tag: any) => tag.text) || []),
    ];
    return (
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {tags.map((tag) => (
          <Chip size="small" variant="outlined" label={tag} key={tag} />
        ))}
      </Box>
    );
  };

  const renderDelete = ({ row }: any) => (
    <Tooltip title="Delete localization">
      <IconButton
        id="delete_button"
        size="small"
        color="error"
        onClick={() => openDialog(row.dateobs, row.localization_name)}
      >
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  );

  const columns: any[] = [
    {
      field: "created_at",
      headerName: "Created at",
      width: 170,
      valueFormatter: (value: string) =>
        dayjs.utc(value).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      field: "localization_name",
      headerName: "Name",
      flex: 2,
      minWidth: 280,
      sortable: false,
      renderCell: renderName,
    },
    {
      field: "Center",
      headerName: "Center",
      flex: 2,
      minWidth: 300,
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
      width: 130,
      sortable: false,
      valueGetter: (_value: any, row: any) => row[name],
    })),
    {
      field: "delete",
      headerName: "",
      width: 60,
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
        getRowHeight={() => "auto"}
        hideFooter={localizations.length <= 25}
        sx={{
          "& .MuiDataGrid-cell": { display: "flex", alignItems: "center" },
        }}
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
