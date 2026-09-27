import { useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetSpatialCatalogsQuery,
  useGetSpatialCatalogQuery,
  useDeleteSpatialCatalogMutation,
} from "../../ducks/spatialCatalogs";
import { useFetchSpatialCatalogSourcesQuery } from "../../ducks/sources";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ListPanelPage from "../ListPanelPage";
import SourceTable from "../source/SourceTable";
import SpatialCatalogTable from "./SpatialCatalogTable";
import NewSpatialCatalog from "./NewSpatialCatalog";

interface SpatialCatalogSourcesArgs {
  catalogName: string;
  entryName: string;
  filterParams?: any;
}

interface SpatialCatalogSourcesProps {
  sourcesArgs: SpatialCatalogSourcesArgs;
  setSourcesArgs: (args: SpatialCatalogSourcesArgs) => void;
}

const SpatialCatalogSources = ({
  sourcesArgs,
  setSourcesArgs,
}: SpatialCatalogSourcesProps) => {
  const { data } = useFetchSpatialCatalogSourcesQuery(sourcesArgs);
  const setFilterParams = (filterParams: any) =>
    setSourcesArgs({ ...sourcesArgs, filterParams });

  if (!data?.sources?.length) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        No sources within entry localization.
      </Typography>
    );
  }

  return (
    <SourceTable
      title=""
      sources={data.sources}
      paginateCallback={(
        pageNumber: number,
        numPerPage: number,
        sortData: any,
        filterData: any,
      ) =>
        setFilterParams({
          ...filterData,
          pageNumber,
          numPerPage,
          ...(sortData?.name && {
            sortBy: sortData.name,
            sortOrder: sortData.direction,
          }),
        })
      }
      pageNumber={data.pageNumber}
      totalMatches={data.totalMatches}
      numPerPage={data.numPerPage}
      sortingCallback={(sortData: any, filterData: any) =>
        setFilterParams({
          ...filterData,
          pageNumber: 1,
          numPerPage: data.numPerPage,
          sortBy: sortData.name,
          sortOrder: sortData.direction,
        })
      }
    />
  );
};

const SpatialCatalogPage = () => {
  const dispatch = useAppDispatch();
  const { data: catalogs = [] } = useGetSpatialCatalogsQuery();
  const [deleteSpatialCatalog] = useDeleteSpatialCatalogMutation();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [catalogToDelete, setCatalogToDelete] = useState<number | null>(null);
  const [sourcesArgs, setSourcesArgs] =
    useState<SpatialCatalogSourcesArgs | null>(null);
  const currentId = catalogs.some((c: any) => c.id === selectedId)
    ? selectedId
    : (catalogs[0]?.id ?? null);
  const { data: catalog } = useGetSpatialCatalogQuery(currentId!, {
    skip: !currentId,
  });
  const isAdmin =
    useGetProfileQuery().data?.permissions?.includes("System admin");

  const deleteCatalog = async () => {
    try {
      await deleteSpatialCatalog(catalogToDelete!).unwrap();
      dispatch(
        showNotification("Spatial catalog deleting... please be patient."),
      );
      setCatalogToDelete(null);
    } catch {
      // error notification is dispatched by the base query
    }
  };

  const selectCatalog = (id: number) => {
    setSelectedId(id);
    setSourcesArgs(null);
  };

  return (
    <>
      <ListPanelPage
        name="Spatial Catalog"
        permission="System admin"
        main={
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {currentId ? (
              <SpatialCatalogTable
                catalog={catalog}
                setSourcesArgs={setSourcesArgs}
              />
            ) : (
              <Typography sx={{ color: "text.secondary" }}>
                No spatial catalogs available.
              </Typography>
            )}
            {sourcesArgs && (
              <SpatialCatalogSources
                sourcesArgs={sourcesArgs}
                setSourcesArgs={setSourcesArgs}
              />
            )}
          </Box>
        }
        items={catalogs.map((c: any) => ({
          key: c.id,
          title: c.catalog_name,
          lines: [`${c.entries_count} entries`],
          buttonProps: {
            selected: c.id === currentId,
            onClick: () => selectCatalog(c.id),
          },
          action: isAdmin && (
            <IconButton
              id="delete_button"
              onClick={() => setCatalogToDelete(c.id)}
            >
              <DeleteIcon />
            </IconButton>
          ),
        }))}
        form={<NewSpatialCatalog />}
      />
      <ConfirmDeletionDialog
        deleteFunction={deleteCatalog}
        dialogOpen={catalogToDelete !== null}
        closeDialog={() => setCatalogToDelete(null)}
        resourceName="spatial catalog"
      />
    </>
  );
};

export default SpatialCatalogPage;
