import Typography from "@mui/material/Typography";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

interface GcnPropertiesProps {
  properties: any[];
}

const GcnProperties = ({ properties }: GcnPropertiesProps) => {
  if (!properties || properties.length === 0) {
    return (
      <Typography variant="body2">No properties for this event...</Typography>
    );
  }

  // Flatten each property's "data" dict into one column per property name.
  const propertyNames = properties
    .map((property) => Object.keys(property.data))
    .flat();
  const uniquePropertyNames = [...new Set(propertyNames)];

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
      valueGetter: (_value: any, row: any) => row[name],
    })),
  ];

  return (
    <StyledDataGrid
      autoHeight
      rows={propertiesWithUniqueKeys}
      columns={columns}
      getRowId={(row: any) => row.__rowid}
      initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
      pageSizeOptions={[1, 10, 15]}
      slots={{ toolbar: DataGridToolbar }}
      slotProps={{ toolbar: { title: "Event Properties" } }}
      showToolbar
    />
  );
};

export default GcnProperties;
