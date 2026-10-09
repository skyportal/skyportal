import { ReactNode, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import JoinInnerIcon from "@mui/icons-material/JoinInner";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import FilterListIcon from "@mui/icons-material/FilterList";
import Close from "@mui/icons-material/Close";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import dayjs from "dayjs";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
import ExpandableCell from "../ExpandableCell";
import Spinner from "../Spinner";

import { filterOutEmptyValues } from "../../API";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";
import { useGetConfigQuery } from "../../ducks/config";
import { useIsReadOnly } from "../../ducks/profile";
import GcnAssociationRules from "./GcnAssociationRules";
import GcnEventsFilterForm from "./GcnEventsFilterForm";
import NewGcnEvent from "./NewGcnEvent";
import DefaultGcnTagPage from "./DefaultGcnTagPage";
import Crossmatch from "./CrossmatchGcnEvents";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";

const DEFAULT_NUM_PER_PAGE = 25;
const FILTER_KEYS = [
  "startDate",
  "endDate",
  "gcnTagKeep",
  "gcnTagRemove",
  "gcnPropertiesFilter",
  "localizationTagKeep",
  "localizationTagRemove",
  "localizationPropertiesFilter",
  "groupIds",
];

type DialogName = "filter" | "new" | "crossmatch" | "defaultTag";

const stackedItemSx = {
  width: "100%",
  position: "relative",
  "&:not(:first-of-type)": {
    mt: 1.5,
    "&::before": {
      content: '""',
      position: "absolute",
      top: "-8px",
      left: 0,
      width: "20%",
      height: "1px",
      bgcolor: "grey.400",
    },
  },
};

const GcnDialog = ({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) => (
  <Dialog open onClose={onClose} maxWidth="md">
    <DialogTitle sx={{ p: 2 }}>
      <Typography sx={{ mr: 2, fontSize: "1.5rem" }}>{title}</Typography>
      <IconButton
        aria-label="close"
        onClick={onClose}
        sx={{ position: "absolute", right: 8, top: 8, color: "grey.500" }}
      >
        <Close />
      </IconButton>
    </DialogTitle>
    <DialogContent dividers>{children}</DialogContent>
  </Dialog>
);

const GcnEventsToolbar = ({
  search,
  onSearchChange,
  onOpen,
}: {
  search: string;
  onSearchChange: (text: string) => void;
  onOpen: (dialog: DialogName) => void;
}) => {
  const isReadOnly = useIsReadOnly();
  return (
    <DataGridToolbar
      title="GCN Events"
      showQuickFilter={false}
      showExport={false}
      showExpandAll
    >
      <Tooltip title="Filter Table">
        <IconButton
          size="small"
          data-testid="Filter Table-iconButton"
          onClick={() => onOpen("filter")}
        >
          <FilterListIcon />
        </IconButton>
      </Tooltip>
      <TextField
        variant="standard"
        size="small"
        placeholder="Search"
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
      />
      {!isReadOnly && (
        <IconButton name="new_gcnevent" onClick={() => onOpen("new")}>
          <AddIcon />
        </IconButton>
      )}
      <IconButton
        name="crossmatch_gcnevents"
        onClick={() => onOpen("crossmatch")}
      >
        <JoinInnerIcon />
      </IconButton>
      <IconButton name="default_gcn_tags" onClick={() => onOpen("defaultTag")}>
        <LocalOfferIcon />
      </IconButton>
    </DataGridToolbar>
  );
};

const GcnEvents = () => {
  const dispatch = useAppDispatch();
  const gcnTagsClasses = useGetConfigQuery().data?.["gcnTagsClasses"] as
    Record<string, string> | undefined;

  const [dialog, setDialog] = useState<DialogName | null>(null);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [tab, setTab] = useState(0);
  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: DEFAULT_NUM_PER_PAGE,
  });

  const { data: gcnEvents } = useGetGcnEventsQuery(fetchParams);

  if (!gcnEvents) return <Spinner context="GCN events" />;

  const updateParams = (patch: Record<string, any>) =>
    setFetchParams({ ...fetchParams, ...patch });
  const handleClose = () => setDialog(null);

  const handleFilterSubmit = (formData: any) => {
    const data: Record<string, any> = filterOutEmptyValues(formData, false);
    updateParams({
      pageNumber: 1,
      numPerPage: DEFAULT_NUM_PER_PAGE,
      ...(Object.keys(data).length > 0 &&
        Object.fromEntries(FILTER_KEYS.map((key) => [key, data[key]]))),
    });
    dispatch(showNotification("Filters submitted to server"));
    handleClose();
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    updateParams({
      pageNumber: 1,
      ...(model[0] && { sortBy: model[0].field, sortOrder: model[0].sort }),
    });
  };

  const columns: any[] = [
    {
      field: "dateobs",
      headerName: "Date Observed",
      minWidth: 180,
      sortable: true,
      renderCell: ({ row }: any) => (
        <Link
          component={RouterLink}
          to={`/gcn_events/${row.dateobs}`}
          underline="hover"
        >
          {dayjs(row.dateobs).format("YYYY-MM-DD HH:mm:ss")}
        </Link>
      ),
    },
    {
      field: "aliases",
      headerName: "Aliases",
      minWidth: 120,
      valueGetter: (value: string[] | undefined) => value?.join(", "),
    },
    {
      field: "gcn_tags",
      headerName: "Event Tags",
      minWidth: 120,
      renderCell: ({ row }: any) => (
        <ExpandableCell
          items={[...new Set<string>(row.tags ?? [])].map((tag) => (
            <Chip
              size="small"
              key={tag}
              label={tag}
              sx={{ bgcolor: gcnTagsClasses?.[tag] ?? "#999999" }}
            />
          ))}
        />
      ),
    },
    {
      field: "allocation_triggers",
      headerName: "Allocation Triggers",
      renderCell: ({ row }: any) => (
        <GcnEventAllocationTriggers gcnEvent={row} showPassed />
      ),
    },
    {
      field: "localization_tags",
      headerName: "Localization Tags",
      renderCell: ({ row }: any) => (
        <ExpandableCell
          items={[
            ...new Set<string>(
              row.localizations?.flatMap((loc: any) =>
                (loc.tags ?? []).map((tag: any) => tag.text),
              ),
            ),
          ].map((tag) => (
            <Chip size="small" key={tag} label={tag} />
          ))}
        />
      ),
    },
    {
      field: "localizations",
      headerName: "Localizations",
      renderCell: ({ row }: any) => (
        <ExpandableCell
          items={(row.localizations ?? []).map((loc: any) => (
            <Box key={loc.id} sx={stackedItemSx}>
              <p>{loc.localization_name}</p>
            </Box>
          ))}
        />
      ),
    },
    {
      field: "gcn_notices",
      headerName: "GCN Notices",
      renderCell: ({ row }: any) => (
        <ExpandableCell
          maxVisible={2}
          items={(row.gcn_notices ?? []).map((notice: any) => (
            <Box key={notice.id} sx={stackedItemSx}>
              <Tooltip title={notice.ivorn} placement="left">
                <p>{notice.stream}</p>
              </Tooltip>
              <Box component="p" sx={{ fontSize: "0.7rem" }}>
                {notice.notice_type}
              </Box>
              <Box component="p" sx={{ fontSize: "0.7rem" }}>
                {notice.date}
              </Box>
            </Box>
          ))}
        />
      ),
    },
  ].map((column) => ({
    flex: 1,
    minWidth: 150,
    sortable: false,
    filterable: false,
    ...column,
  }));

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tab}
        onChange={(_event, value) => setTab(value)}
        aria-label="gcn events tabs"
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Events" />
        <Tab label="Association rules" />
      </Tabs>
      {tab === 0 ? (
        <StyledDataGrid
          height={FULL_PAGE_HEIGHT_WITH_TABS}
          rows={gcnEvents.events || []}
          columns={columns}
          getRowId={(row: any) => row.dateobs}
          getRowHeight={() => "auto"}
          paginationMode="server"
          sortingMode="server"
          rowCount={gcnEvents.totalMatches}
          paginationModel={{
            page: fetchParams.pageNumber - 1,
            pageSize: fetchParams.numPerPage,
          }}
          onPaginationModelChange={(model: any) =>
            updateParams({
              pageNumber: model.page + 1,
              numPerPage: model.pageSize,
            })
          }
          sortModel={sortModel}
          onSortModelChange={handleSortModelChange}
          disableColumnFilter
          slots={{ toolbar: GcnEventsToolbar }}
          slotProps={{
            toolbar: {
              search: fetchParams.partialdateobs ?? "",
              onSearchChange: (text: string) =>
                updateParams({ pageNumber: 1, partialdateobs: text }),
              onOpen: setDialog,
            },
          }}
          showToolbar
        />
      ) : (
        <GcnAssociationRules />
      )}
      <Dialog open={dialog === "filter"} onClose={handleClose} fullWidth>
        <DialogContent>
          <GcnEventsFilterForm handleFilterSubmit={handleFilterSubmit} />
        </DialogContent>
      </Dialog>
      {dialog === "new" && (
        <GcnDialog title="New GCN Event" onClose={handleClose}>
          <NewGcnEvent handleClose={handleClose} />
        </GcnDialog>
      )}
      {dialog === "crossmatch" && (
        <GcnDialog title="Crossmatch GCN Events" onClose={handleClose}>
          <Crossmatch />
        </GcnDialog>
      )}
      {dialog === "defaultTag" && (
        <GcnDialog title="Default Gcn Tags" onClose={handleClose}>
          <DefaultGcnTagPage />
        </GcnDialog>
      )}
    </Box>
  );
};

export default GcnEvents;
