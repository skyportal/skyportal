import { lazy, ReactNode, Suspense, useState } from "react";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton, {
  ListItemButtonProps,
} from "@mui/material/ListItemButton";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";

import { useGetProfileQuery } from "../ducks/profile";
import type { WorldMapMarker } from "./WorldMap";
import Button from "./Button";
import Paper from "./Paper";
import Spinner from "./Spinner";

const WorldMap = lazy(() => import("./WorldMap"));

export interface MapListItem {
  key: string | number;
  title: string;
  lines: string[];
  buttonProps: ListItemButtonProps & Record<string, any>;
}

const panelStyles = (isSelected: boolean) => ({
  color: "text.secondary",
  width: "50%",
  transition: "background-color 0.3s ease",
  boxShadow: "0 -4px 8px -4px rgba(0, 0, 0, 0.2)",
  borderBottomRightRadius: 0,
  borderBottomLeftRadius: 0,
  "&:hover": {
    boxShadow: isSelected
      ? "0 -4px 8px -4px rgba(0, 0, 0, 0.2)"
      : "0 -3px 8px -5px rgba(0, 0, 0, 0.2)",
    backgroundColor: isSelected
      ? "background.paper"
      : "action.disabledBackground",
  },
  ...(isSelected && {
    zIndex: 3,
    backgroundColor: "background.paper",
    borderBottom: "none",
  }),
});

const ItemList = ({
  items,
  isMobile,
}: {
  items: MapListItem[];
  isMobile: boolean;
}) => (
  <List>
    {items.map(({ key, title, lines, buttonProps }) => (
      <ListItemButton
        key={key}
        sx={{ flexDirection: "column", textAlign: "center" }}
        divider
        {...buttonProps}
      >
        <Typography
          variant={(isMobile ? "h7" : "h6") as any}
          sx={{ fontWeight: "400" }}
        >
          {title}
        </Typography>
        {lines.map((line) => (
          <Typography
            key={line}
            variant={isMobile ? "body2" : "body1"}
            sx={{ color: "text.secondary" }}
          >
            {line}
          </Typography>
        ))}
      </ListItemButton>
    ))}
  </List>
);

interface MapListPageProps {
  name: string;
  markers: WorldMapMarker[];
  items: MapListItem[];
  form: ReactNode;
}

const MapListPage = ({ name, markers, items, form }: MapListPageProps) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const { data: currentUser } = useGetProfileQuery();
  const canManage = currentUser?.permissions?.includes("Manage allocations");
  const [showForm, setShowForm] = useState(false);

  return (
    <Suspense fallback={<Spinner />}>
      <Grid container spacing={3}>
        <Grid size={{ lg: 8, md: 6, sm: 12 }}>
          <Paper>
            {isMobile ? (
              <>
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  List of {name}s
                </Typography>
                <ItemList items={items} isMobile />
              </>
            ) : (
              <WorldMap markers={markers} />
            )}
          </Paper>
        </Grid>
        {(!isMobile || canManage) && (
          <Grid size={{ lg: 4, md: 6, sm: 12 }}>
            {!isMobile && canManage && (
              <Box>
                <Button
                  secondary
                  onClick={() => setShowForm(false)}
                  sx={panelStyles(!showForm)}
                >
                  {name}s
                </Button>
                <Button
                  secondary
                  onClick={() => setShowForm(true)}
                  sx={panelStyles(showForm)}
                >
                  <AddIcon />
                </Button>
              </Box>
            )}
            <Paper>
              {isMobile && (
                <Typography variant="h6" sx={{ fontWeight: "500" }}>
                  Add a New {name}
                </Typography>
              )}
              {canManage && (showForm || isMobile) ? (
                form
              ) : (
                <ItemList items={items} isMobile={false} />
              )}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Suspense>
  );
};

export default MapListPage;
