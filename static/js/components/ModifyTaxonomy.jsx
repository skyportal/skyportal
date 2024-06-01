import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import { fetchTaxonomies, modifyTaxonomy } from "../ducks/taxonomies";

import GroupShareSelect from "./group/GroupShareSelect";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  taxonomySelect: {
    width: "100%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const ModifyTaxonomy = () => {
  const classes = useStyles();

  const [selectedTaxonomyId, setSelectedTaxonomyId] = useState(null);
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const dispatch = useDispatch();

  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const handleSubmit = async ({ formData }) => {
    if (selectedGroupIds.length > 0) {
      formData.group_ids = selectedGroupIds;
    }

    const result = await dispatch(modifyTaxonomy(selectedTaxonomyId, formData));
    if (result.status === "success") {
      dispatch(showNotification("Taxonomy saved"));
      dispatch(fetchTaxonomies());
    }
  };

  useEffect(() => {
    const getTaxonomies = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(fetchTaxonomies());

      const { data } = result;
      setSelectedTaxonomyId(data[0]?.id);
    };

    getTaxonomies();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedTaxonomyId]);

  if (taxonomyList.length === 0 || !selectedTaxonomyId) {
    return <h3>No taxonomies available...</h3>;
  }

  const taxonomyLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  taxonomyList?.forEach((tax) => {
    taxonomyLookUp[tax.id] = tax;
  });

  const handleSelectedTaxonomyChange = (e) => {
    setSelectedTaxonomyId(e.target.value);
  };

  const taxonomyFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
        description:
          "Short string to make this taxonomy memorable to end users.",
      },
      version: {
        type: "string",
        title: "Version",
        description: "Semantic version of this taxonomy",
      },
      provenance: {
        type: "string",
        title: "Provenance",
        description:
          "Identifier (e.g., URL or git hash) that uniquely ties this taxonomy back to an origin or place of record.",
      },
    },
  };

  return (
    <div className={classes.container}>
      <InputLabel id="taxonomySelectLabel">Taxonomy</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="taxonomySelectLabel"
        value={selectedTaxonomyId}
        onChange={handleSelectedTaxonomyChange}
        name="modifyTaxonomySelect"
        className={classes.taxonomySelect}
      >
        {taxonomyList?.map((taxonomy) => (
          <MenuItem
            value={taxonomy.id}
            key={taxonomy.id}
            className={classes.taxonomySelectItem}
          >
            {`${taxonomy.name}`}
          </MenuItem>
        ))}
      </Select>
      <Form
        schema={taxonomyFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </div>
  );
};

export default ModifyTaxonomy;
