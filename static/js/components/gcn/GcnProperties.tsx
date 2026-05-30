import React from "react";
import { makeStyles } from "tss-react/mui";

import StyledDataGrid from "../StyledDataGrid";

const useStyles = makeStyles()(() => ({
  accordion: {
    width: "100%",
  },
  container: {
    margin: "0rem 0",
    width: "100%",
  },
}));

interface GcnPropertiesProps {
  properties: any[];
}

const GcnProperties = ({ properties }: GcnPropertiesProps) => {
  const { classes } = useStyles();

  if (!properties || properties.length === 0) {
    return <p>No properties for this event...</p>;
  }

  // properties list of dicts each with a "created_at" key and a "data" key
  // we want to refactor that to a list of dicts with a "created_at" key and
  // a key for each property name

  // that means that first we need the list of all property names of all elements in the list
  const propertyNames = properties
    .map((property) => Object.keys(property.data))
    .flat();
  // then we need to remove duplicates
  const uniquePropertyNames = [...new Set(propertyNames)];

  // now we can create a list of dicts with a "created_at" key and a key for each property name
  const propertiesWithUniqueKeys = properties.map((property, index) => {
    const newProperty: Record<string, any> = {
      __rowid: index,
      created_at: property.created_at,
    };
    uniquePropertyNames.forEach((name) => {
      if (Object.keys(property.data).includes(name)) {
        if (typeof property.data[name] === "number") {
          if (property.data[name] > 10000 || property.data[name] < -10000) {
            newProperty[name] = property.data[name].toExponential(4);
          } else if (
            property.data[name] > 0.0001 ||
            property.data[name] < -0.0001
          ) {
            newProperty[name] = property.data[name].toFixed(4);
          } else if (property.data[name] === 0) {
            newProperty[name] = 0;
          } else {
            newProperty[name] = property.data[name].toExponential(4);
          }
        } else {
          newProperty[name] = property.data[name];
        }
      } else {
        newProperty[name] = null;
      }
    });
    return newProperty;
  });

  const columns: any[] = [
    {
      field: "created_at",
      headerName: "Created at",
      flex: 1,
      minWidth: 160,
      sortable: false,
    },
    ...uniquePropertyNames.map((name) => ({
      field: name,
      headerName: name,
      flex: 1,
      minWidth: 100,
      sortable: false,
      // Property names may contain dots; force flat access rather than letting
      // DataGrid interpret the field as a nested path.
      valueGetter: (value: any, row: any) => row[name],
    })),
  ];

  return (
    <div className={classes.container}>
      <StyledDataGrid
        autoHeight
        rows={propertiesWithUniqueKeys}
        columns={columns}
        getRowId={(row: any) => row.__rowid}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[1, 10, 15]}
        showToolbar
      />
    </div>
  );
};

export default GcnProperties;
