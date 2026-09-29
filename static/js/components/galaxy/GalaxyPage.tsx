import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetGalaxiesQuery,
  useGetGalaxyCatalogsQuery,
  useDeleteCatalogMutation,
} from "../../ducks/galaxies";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ListPanelPage from "../ListPanelPage";
import GalaxyTable from "./GalaxyTable";
import NewGalaxy from "./NewGalaxy";

const GalaxyPage = () => {
  const dispatch = useAppDispatch();
  const isAdmin =
    useGetProfileQuery().data?.permissions?.includes("System admin");
  const { data: catalogs = [] } = useGetGalaxyCatalogsQuery();
  const [deleteCatalog] = useDeleteCatalogMutation();
  const [catalogToDelete, setCatalogToDelete] = useState<string | null>(null);
  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: 25,
  });
  const { data: galaxies } = useGetGalaxiesQuery(fetchParams);

  const selectCatalog = (catalog_name?: string) =>
    setFetchParams((prev: any) => ({ ...prev, catalog_name, pageNumber: 1 }));

  const confirmDelete = async () => {
    try {
      await deleteCatalog(catalogToDelete!).unwrap();
      dispatch(showNotification("Catalog deleting... please be patient."));
      if (fetchParams.catalog_name === catalogToDelete) selectCatalog();
      setCatalogToDelete(null);
    } catch {
      // error notification handled by the baseQuery
    }
  };

  return (
    <>
      <ListPanelPage
        name="Galaxy Catalog"
        permission="System admin"
        main={
          <GalaxyTable
            fixedHeader
            title={fetchParams.catalog_name ?? "All catalogs"}
            galaxies={galaxies?.galaxies}
            totalMatches={galaxies?.totalMatches}
            pageNumber={fetchParams.pageNumber}
            numPerPage={fetchParams.numPerPage}
            onFilterSubmit={(data) =>
              setFetchParams((prev: any) => ({
                ...prev,
                ...data,
                pageNumber: 1,
              }))
            }
            handleTableChange={(_action: string, { page, rowsPerPage }: any) =>
              setFetchParams((prev: any) => ({
                ...prev,
                numPerPage: rowsPerPage,
                pageNumber: page + 1,
              }))
            }
          />
        }
        items={catalogs.map(({ catalog_name, catalog_count }: any) => ({
          key: catalog_name,
          title: catalog_name,
          lines: [`${catalog_count} galaxies`],
          buttonProps: {
            selected: catalog_name === fetchParams.catalog_name,
            onClick: () =>
              selectCatalog(
                catalog_name === fetchParams.catalog_name
                  ? undefined
                  : catalog_name,
              ),
          },
          action: isAdmin && (
            <IconButton onClick={() => setCatalogToDelete(catalog_name)}>
              <DeleteIcon />
            </IconButton>
          ),
        }))}
        form={<NewGalaxy />}
      />
      <ConfirmDeletionDialog
        deleteFunction={confirmDelete}
        dialogOpen={catalogToDelete !== null}
        closeDialog={() => setCatalogToDelete(null)}
        resourceName="galaxy catalog"
      />
    </>
  );
};

export default GalaxyPage;
