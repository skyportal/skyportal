import { useGetProfileQuery } from "../../ducks/profile";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import TaxonomyTable from "./TaxonomyTable";

const TaxonomyList = () => {
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();
  const { data: currentUser } = useGetProfileQuery();
  const isSystemAdmin =
    currentUser?.permissions?.includes("System admin") || false;
  const managePermission =
    currentUser?.permissions?.includes("Post taxonomy") || isSystemAdmin;
  const deletePermission =
    currentUser?.permissions?.includes("Delete taxonomy") || isSystemAdmin;

  return (
    <TaxonomyTable
      taxonomies={taxonomyList}
      managePermission={managePermission}
      deletePermission={deletePermission}
    />
  );
};

export default TaxonomyList;
