import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import TaxonomyTableComponent from "./TaxonomyTable";
import Spinner from "../Spinner";

import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";

const TaxonomyTable = TaxonomyTableComponent as any;

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    maxWidth: "44.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paper: {},
  paperContent: {
    padding: "1rem",
  },
  taxonomyDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  taxonomyDeleteDisabled: {
    opacity: 0,
  },
}));

export function taxonomyTitle(taxonomy: any) {
  if (!taxonomy?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${taxonomy?.name}`;

  return result;
}

export function taxonomyInfo(taxonomy: any) {
  if (!taxonomy?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const groupNames: string[] = [];
  taxonomy?.groups?.forEach((group: any) => {
    groupNames.push(group.name);
  });

  let result = "";

  if (taxonomy?.provenance || taxonomy?.version || taxonomy?.isLatest) {
    result += "( ";
    if (taxonomy?.isLatest) {
      result += `isLatest: ${taxonomy?.isLatest}`;
    }
    if (taxonomy?.provenance) {
      result += ` / Provenance: ${taxonomy?.provenance}`;
    }
    if (taxonomy?.version) {
      result += ` / Version: ${taxonomy?.version}`;
    }
    if (groupNames.length > 0) {
      const groups_str = groupNames.join(", ");
      result += ` / groups: ${groups_str}`;
    }
    result += " )";
  }

  return result;
}

const TaxonomyList = () => {
  const { classes } = useStyles();

  const { data: taxonomyList, refetch } = useGetTaxonomiesQuery();

  const { data: currentUser } = useGetProfileQuery();
  const permission = currentUser?.permissions?.includes("System admin");

  const [, setRowsPerPage] = useState(100);

  const handleTaxonomyTablePagination = (
    _pageNumber: number,
    numPerPage: number,
  ) => {
    setRowsPerPage(numPerPage);
    refetch();
  };

  const handleTaxonomyTableSorting = () => {
    refetch();
  };

  if (taxonomyList == null) {
    return <Spinner />;
  }

  return (
    <div className={classes.paper}>
      <Typography variant="h6" display="inline" />
      {taxonomyList && (
        <TaxonomyTable
          taxonomies={taxonomyList}
          managePermission={permission}
          paginateCallback={handleTaxonomyTablePagination}
          totalMatches={undefined}
          pageNumber={undefined}
          numPerPage={undefined}
          sortingCallback={handleTaxonomyTableSorting}
        />
      )}
    </div>
  );
};

const TaxonomyPage = () => (
  <Grid container spacing={3}>
    <Grid size={12}>
      <TaxonomyList />
    </Grid>
  </Grid>
);

export default TaxonomyPage;
