import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { Controller, useForm } from "react-hook-form";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import SpatialCatalogTable from "./SpatialCatalogTable";
import NewSpatialCatalog from "./NewSpatialCatalog";
import SourceTable from "../source/SourceTable";

import {
  useGetSpatialCatalogsQuery,
  useGetSpatialCatalogQuery,
  useDeleteSpatialCatalogMutation,
} from "../../ducks/spatialCatalogs";
import { useFetchSpatialCatalogSourcesQuery } from "../../ducks/sources";

interface SpatialCatalogSourcesArgs {
  catalogName: string;
  entryName: string;
  filterParams?: any;
}

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  header: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  content: {
    margin: "1rem",
  },
  paperContent: {
    padding: "1rem",
    marginBottom: "1rem",
  },
  dividerHeader: {
    background: theme.palette.primary.main,
    height: "2px",
  },
  divider: {
    background: theme.palette.secondary.main,
  },
  catalogDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  catalogDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles()(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

interface SpatialCatalogSourcesPageProps {
  sourcesArgs: SpatialCatalogSourcesArgs | null;
  setSourcesArgs: (args: SpatialCatalogSourcesArgs) => void;
}

const SpatialCatalogSourcesPage = ({
  sourcesArgs,
  setSourcesArgs,
}: SpatialCatalogSourcesPageProps) => {
  const { classes } = useStyles();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);

  const { data: spatialCatalogSources } = useFetchSpatialCatalogSourcesQuery(
    sourcesArgs!,
    { skip: sourcesArgs == null },
  );

  const handleSourcesTableSorting = (sortData: any, filterData: any) => {
    if (sourcesArgs == null) {
      return;
    }
    setSourcesArgs({
      catalogName: sourcesArgs.catalogName,
      entryName: sourcesArgs.entryName,
      filterParams: {
        ...filterData,
        pageNumber: 1,
        numPerPage: sourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      },
    });
  };

  const handleSourcesTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    if (sourcesArgs == null) {
      return;
    }
    setSourcesRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setSourcesArgs({
      catalogName: sourcesArgs.catalogName,
      entryName: sourcesArgs.entryName,
      filterParams: data,
    });
  };

  if (
    !spatialCatalogSources?.sources ||
    spatialCatalogSources.sources.length === 0
  ) {
    return (
      <div className={(classes as any).noSources}>
        <Typography variant="h5">Entry sources</Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources within entry localization.
        </Typography>
      </div>
    );
  }

  return (
    <div className={(classes as any).sourceList}>
      <SourceTable
        title=""
        sources={spatialCatalogSources.sources}
        paginateCallback={handleSourcesTablePagination}
        pageNumber={spatialCatalogSources.pageNumber}
        totalMatches={spatialCatalogSources.totalMatches}
        numPerPage={spatialCatalogSources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
      />
    </div>
  );
};

interface SpatialCatalogListProps {
  catalogs?: any[] | null;
  deletePermission: boolean;
}

const SpatialCatalogList = ({
  catalogs = null,
  deletePermission,
}: SpatialCatalogListProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();
  const { classes: textClasses } = textStyles();
  const [deleteSpatialCatalog] = useDeleteSpatialCatalogMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [catalogToDelete, setCatalogToDelete] = useState<any>(null);
  const openDialog = (id: any) => {
    setDialogOpen(true);
    setCatalogToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setCatalogToDelete(null);
  };

  const deleteCatalog = async () => {
    try {
      await deleteSpatialCatalog(catalogToDelete).unwrap();
      dispatch(
        showNotification("Spatial catalog deleting... please be patient."),
      );
      closeDialog();
    } catch {
      // error notification is dispatched by the base query
    }
  };

  if (!Array.isArray(catalogs)) {
    return <p>Waiting for spatial catalogs to load...</p>;
  }

  return (
    <div className={classes.root}>
      <List component="nav">
        {catalogs?.map((catalog: any) => (
          <ListItem key={catalog}>
            <ListItemText
              primary={catalog.catalog_name}
              secondary={`${catalog.entries_count} entries`}
              classes={textClasses}
            />
            <Button
              id="delete_button"
              classes={{
                root: classes.catalogDelete,
                disabled: classes.catalogDeleteDisabled,
              }}
              onClick={() => openDialog(catalog.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteCatalog}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="galaxy catalog"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const SpatialCatalogPage = () => {
  const { data: spatialCatalogs } = useGetSpatialCatalogsQuery();
  const [selectedSpatialCatalogId, setSelectedSpatialCatalogId] =
    useState<any>(null);
  const [sourcesArgs, setSourcesArgs] =
    useState<SpatialCatalogSourcesArgs | null>(null);

  const { data: spatialCatalog } = useGetSpatialCatalogQuery(
    selectedSpatialCatalogId,
    { skip: !selectedSpatialCatalogId },
  );

  const { data: currentUser } = useGetProfileQuery();
  const { classes } = useStyles();

  const { handleSubmit, control, reset, getValues } = useForm();

  const spatialCatalogsSelect = spatialCatalogs
    ? [
        {
          id: -1,
          catalog_name: "Choose catalog",
        },
        ...spatialCatalogs,
      ]
    : [];

  if (spatialCatalogs == null) {
    return <p>No Spatial Catalogs available...</p>;
  }

  const permission =
    currentUser?.permissions?.includes("System admin") ?? false;

  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 6, sm: 12 }}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Spatial Catalogs</Typography>
            <SpatialCatalogList
              catalogs={spatialCatalogs}
              deletePermission={permission}
            />
          </div>
        </Paper>
        <Paper elevation={1}>
          <form className={classes.root} onSubmit={handleSubmit as any}>
            <div className={(classes as any).formItemRightColumn}>
              <Typography
                variant="subtitle2"
                className={(classes as any).title}
              >
                Choose Spatial Catalog
              </Typography>
              <div className={(classes as any).selectItems}>
                <Controller
                  render={({ field: { value } }) => (
                    <Select
                      inputProps={{ MenuProps: { disableScrollLock: true } }}
                      labelId="spatialCatalogSelectLabel"
                      value={value || ""}
                      onChange={(event) => {
                        reset({
                          ...getValues(),
                          spatialcatalogid:
                            event.target.value === -1 ? "" : event.target.value,
                        });
                        setSelectedSpatialCatalogId(event.target.value);
                      }}
                      className={(classes as any).select}
                    >
                      {spatialCatalogsSelect?.map((cat: any) => (
                        <MenuItem
                          value={cat.id}
                          key={cat.id}
                          className={(classes as any).selectItem}
                        >
                          {`${cat.catalog_name}`}
                        </MenuItem>
                      ))}
                    </Select>
                  )}
                  name="spatialcatalogid"
                  control={control}
                  defaultValue=""
                />
              </div>
            </div>
          </form>
          <div className={classes.paperContent}>
            <Typography variant="h5">List of Catalog Entries</Typography>
            <SpatialCatalogTable
              catalog={spatialCatalog}
              setSourcesArgs={setSourcesArgs}
            />
          </div>
          <div className={classes.paperContent}>
            <SpatialCatalogSourcesPage
              sourcesArgs={sourcesArgs}
              setSourcesArgs={setSourcesArgs}
            />
          </div>
        </Paper>
      </Grid>
      {currentUser?.permissions?.includes("System admin") && (
        <Grid size={{ md: 6, sm: 12 }}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h5">Add New Spatial Catalog</Typography>
              <NewSpatialCatalog />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default SpatialCatalogPage;
