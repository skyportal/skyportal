import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import { fetchTaxonomies, modifyTaxonomy } from "../../ducks/taxonomies";

import GroupShareSelect from "../group/GroupShareSelect";

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

const ModifyTaxonomy = ({ taxonomy_id, onClose }) => {
  const classes = useStyles();

  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const dispatch = useDispatch();

  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const handleSubmit = async ({ formData }) => {
    if (selectedGroupIds.length > 0) {
      formData.group_ids = selectedGroupIds;
    }

    const result = await dispatch(modifyTaxonomy(taxonomy_id, formData));
    if (result.status === "success") {
      dispatch(showNotification("Taxonomy saved"));
      dispatch(fetchTaxonomies());
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  const taxonomyLookUp = {};

  taxonomyList?.forEach((tax) => {
    taxonomyLookUp[tax.id] = tax;
  });

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

ModifyTaxonomy.propTypes = {
  taxonomy_id: PropTypes.number.isRequired,
  onClose: PropTypes.func,
};

ModifyTaxonomy.defaultProps = {
  onClose: null,
};

export default ModifyTaxonomy;
