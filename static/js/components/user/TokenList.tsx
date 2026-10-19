import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ExpandableCell from "../ExpandableCell";
import UpdateTokenACLs from "./UpdateTokenACLs";
import SharePage from "../SharePage";

import {
  useDeleteTokenMutation,
  useGetProfileQuery,
} from "../../ducks/profile";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";

dayjs.extend(utc);

const TokenListToolbar = () => (
  <DataGridToolbar title="My Tokens" showExpandAll />
);

interface TokenListProps {
  tokens: any[];
}

const TokenList = ({ tokens }: TokenListProps) => {
  const [deleteToken] = useDeleteTokenMutation();
  const { data: profile } = useGetProfileQuery();

  if (!tokens) return null;

  const columns: any[] = [
    {
      field: "id",
      headerName: "Value",
      width: 400,
      sortable: false,
      renderCell: ({ value }: any) => (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            width: "100%",
          }}
        >
          <TextField
            value={value}
            size="small"
            fullWidth
            slotProps={{ htmlInput: { readOnly: true } }}
          />
          <Button
            secondary
            size="small"
            sx={{ flexShrink: 0 }}
            onClick={() => navigator.clipboard.writeText(value)}
          >
            Copy
          </Button>
        </div>
      ),
    },
    {
      field: "qr",
      headerName: "QR",
      width: 70,
      sortable: false,
      renderCell: ({ row }: any) => <SharePage value={row.id} />,
    },
    { field: "name", headerName: "Name", width: 130 },
    {
      field: "acls",
      headerName: "ACLs",
      flex: 1,
      minWidth: 320,
      sortable: false,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <ExpandableCell
            maxVisible={5}
            items={(row.acls || []).map((acl: string) => (
              <Chip key={acl} label={acl} size="small" />
            ))}
          />
          <UpdateTokenACLs
            tokenId={row.id}
            currentACLs={row.acls}
            availableACLs={profile?.permissions ?? []}
          />
        </Box>
      ),
    },
    {
      field: "created_at",
      headerName: "Created",
      width: 150,
      valueFormatter: (value: any) =>
        value ? dayjs.utc(value).format("YYYY/MM/DD HH:mm") : "",
    },
    {
      field: "delete",
      headerName: "Delete",
      width: 90,
      sortable: false,
      renderCell: ({ row }: any) => (
        <IconButton
          aria-label="Delete token"
          color="error"
          onClick={() => deleteToken(row.id)}
        >
          <DeleteIcon />
        </IconButton>
      ),
    },
  ];

  return (
    <StyledDataGrid
      autoHeight
      rows={tokens}
      columns={columns}
      getRowId={(row: any) => row.id}
      getRowHeight={() => "auto"}
      sx={{ "& .MuiDataGrid-cell": { whiteSpace: "normal", py: 1 } }}
      slots={{ toolbar: TokenListToolbar }}
      showToolbar
    />
  );
};

export default TokenList;
