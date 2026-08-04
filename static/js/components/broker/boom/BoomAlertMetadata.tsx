import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import { AlertOption } from "../BrokerAlertCard";

const num = (v: unknown, d: number) =>
  typeof v === "number" ? v.toFixed(d) : "—";

const str = (v: unknown) => (v == null ? "—" : String(v));

const COLUMNS = (isLSST: boolean) => [
  {
    label: isLSST ? "diaSourceId" : "candid",
    value: (a: any, raw: any) =>
      str(raw?.diaSourceId ?? a.candid ?? raw?.candid ?? raw?._id),
  },
  { label: "JD", value: (a: any) => num(a.jd, 5) },
  { label: "band", value: (_a: any, raw: any) => str(raw?.candidate?.band) },
  { label: "magpsf", value: (a: any) => num(a.magpsf, 3) },
  {
    label: "sigmapsf",
    value: (_a: any, raw: any) => num(raw?.candidate?.sigmapsf, 3),
  },
  {
    label: "isdiffpos",
    value: (_a: any, raw: any) => str(raw?.candidate?.isdiffpos),
  },
  {
    label: isLSST ? "reliability" : "drb",
    value: (_a: any, raw: any) =>
      num(isLSST ? raw?.candidate?.reliability : raw?.candidate?.drb, 5),
  },
  {
    label: "snr",
    value: (_a: any, raw: any) =>
      num(raw?.candidate?.snr_psf ?? raw?.candidate?.snr, 2),
  },
  ...(isLSST
    ? []
    : [
        {
          label: "programid",
          value: (_a: any, raw: any) => str(raw?.candidate?.programid),
        },
      ]),
];

interface BoomAlertMetadataProps {
  alerts: AlertOption[];
  survey: string;
  selectedCandid?: string | number | undefined;
  onSelect: (candid: string | number) => void;
}

const BoomAlertMetadata = ({
  alerts,
  survey,
  selectedCandid,
  onSelect,
}: BoomAlertMetadataProps) => {
  const columns = COLUMNS(survey === "LSST");
  return (
    <Box sx={{ mt: 1, maxHeight: 200, overflow: "auto" }}>
      <Table
        size="small"
        sx={{ "& td, & th": { px: 0.75, fontSize: "0.7rem" } }}
      >
        <TableHead>
          <TableRow>
            {columns.map((c) => (
              <TableCell key={c.label}>{c.label}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {alerts.map((a) => (
            <TableRow
              key={String(a.candid)}
              hover
              selected={a.candid === selectedCandid}
              onClick={() => onSelect(a.candid)}
              sx={{ cursor: "pointer" }}
            >
              {columns.map((c) => (
                <TableCell key={c.label}>{c.value(a, a.raw)}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
};

export default BoomAlertMetadata;
