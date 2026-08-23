import { useState } from "react";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";

import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";

const numPerPage = 10;

interface MMADetectorEventsDialogProps {
  mmadetector: any;
  onClose: () => void;
}

/** The GCN events an MMA detector contributed to. */
const MMADetectorEventsDialog = ({
  mmadetector,
  onClose,
}: MMADetectorEventsDialogProps) => {
  const [pageNumber, setPageNumber] = useState(1);

  const { data, isFetching } = useGetGcnEventsQuery({
    mmadetectorIds: `${mmadetector.id}`,
    numPerPage,
    pageNumber,
  });

  const events = (data as any)?.events ?? [];
  const totalMatches = (data as any)?.totalMatches ?? 0;

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {mmadetector.name} ({mmadetector.nickname})
      </DialogTitle>
      <DialogContent dividers>
        {!isFetching && totalMatches === 0 ? (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No GCN events are linked to this detector.
          </Typography>
        ) : (
          <>
            <Table size="small" data-testid="mmadetector-events-table">
              <TableHead>
                <TableRow>
                  <TableCell>Event</TableCell>
                  <TableCell>Aliases</TableCell>
                  <TableCell>Tags</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events.map((gcnEvent: any) => (
                  <TableRow key={gcnEvent.dateobs} hover>
                    <TableCell>
                      <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
                        {dayjs(gcnEvent.dateobs).format("YYYY-MM-DD HH:mm:ss")}
                      </Link>
                    </TableCell>
                    <TableCell>{(gcnEvent.aliases ?? []).join(", ")}</TableCell>
                    <TableCell>{(gcnEvent.tags ?? []).join(", ")}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={totalMatches}
              page={pageNumber - 1}
              onPageChange={(_, page) => setPageNumber(page + 1)}
              rowsPerPage={numPerPage}
              rowsPerPageOptions={[numPerPage]}
            />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default MMADetectorEventsDialog;
