import { lazy, Suspense, useEffect, useRef, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import { useGetConfigQuery } from "../../ducks/config";

const SpectraPlot = lazy(() => import("../plot/SpectraPlot"));

interface Observation {
  id: string;
  survey: string;
  obs?: string;
  mjd?: number;
  rv_km_s?: number;
  rv_error_km_s?: number;
  snr?: number;
  used_for_rv: boolean;
  spectrum_available: boolean;
  counterpart_check?: string;
}

interface Match {
  _id: string;
  observations: Observation[];
  review?: { span_km_s?: string; detail: string };
  fermi_matches: {
    fermi_name: string;
    inside_95: boolean;
    separation_arcmin: number;
  }[];
}

interface Spectrum {
  traces: { label: string; wavelengths: number[]; fluxes: number[] }[];
  unavailable: number;
}

const surveys: Record<string, string> = {
  lamost_lrs: "LAMOST LRS",
  lamost_lrs_all: "LAMOST LRS",
  lamost_mrs: "LAMOST MRS",
  sdss_bossnet: "SDSS BOSS",
  sdss_legacy: "SDSS Legacy",
  sdss_allspec: "SDSS Allspec",
  sdss_apogee: "SDSS APOGEE",
  desi_exp: "DESI exposure",
  desi_zpix: "DESI HEALPix",
};

const ArchivalRv = ({ sourceId }: { sourceId: string }) => {
  const enabled = useGetConfigQuery().data?.["archivalRvEnabled"] === true;
  const [match, setMatch] = useState<Match | null>();
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [spectra, setSpectra] = useState<Record<string, Spectrum>>({});
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  if (!enabled) return null;

  const query = async (observation?: Observation) => {
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(undefined);
    setNotice(undefined);
    const path = `/api/sources/${encodeURIComponent(sourceId)}/archival_rv`;
    const suffix = observation
      ? `?${new URLSearchParams({ observation: observation.id })}`
      : "";
    try {
      const response = await fetch(path + suffix, { signal: controller.signal });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.message || "Archival spectroscopy is unavailable.");
      }
      if (!observation) {
        setMatch(result.data.source);
      } else {
        const spectrum: Spectrum = result.data;
        setSpectra((current) => ({ ...current, [observation.id]: spectrum }));
        if (spectrum.unavailable) {
          setNotice("Some wavelength channels were unavailable from the archive.");
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : "Unable to load archive data.");
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const rows = match?.observations || [];
  const lamostRvs = new Set(
    rows.filter((row) => row.survey === "lamost_lrs").map((row) => row.obs),
  );
  const observations = rows
    .filter(
      (row) =>
        (row.spectrum_available || row.rv_km_s != null) &&
        (row.survey !== "lamost_lrs_all" || !lamostRvs.has(row.obs)),
    )
    .sort((a, b) => (a.mjd ?? Infinity) - (b.mjd ?? Infinity));
  const plot = observations.flatMap((row) =>
    (spectra[row.id]?.traces || []).map((trace, index) => ({
      ...trace,
      id: `${row.id}:${index}`,
      type: "object",
      instrument_name: `${surveys[row.survey]} ${trace.label}`,
      telescope_name: surveys[row.survey],
      origin: "Archive",
      observed_at:
        row.mjd == null
          ? null
          : new Date((row.mjd - 40587) * 86400000).toISOString(),
    })),
  );

  return (
    <Box sx={{ width: "100%", mt: 2 }}>
      {match === undefined && (
        <Button disabled={busy} onClick={() => query()}>
          Find archival RVs and spectra
        </Button>
      )}
      {busy && <CircularProgress size={20} aria-label="Loading archive data" />}
      {error && <Alert severity="error">{error}</Alert>}
      {notice && <Alert severity="info">{notice}</Alert>}
      {match === null && <Typography>No match in the archival RV pilot.</Typography>}
      {match && (
        <>
          <Typography variant="subtitle1">Archival spectroscopy · {match._id}</Typography>
          {match.review && (
            <Typography variant="body2">
              {match.review.span_km_s && `Measured spectral shift: ${match.review.span_km_s} km/s. `}
              {match.review.detail}
            </Typography>
          )}
          {match.fermi_matches.map((fermi) => (
            <Typography key={fermi.fermi_name} variant="body2">
              {fermi.fermi_name} · {fermi.separation_arcmin.toFixed(2)}′ from the
              Fermi centroid · {fermi.inside_95 ? "Inside" : "Outside"} 95% ellipse
            </Typography>
          ))}
          {observations.length === 0 ? (
            <Typography>No visit RVs or downloadable spectra for this target.</Typography>
          ) : (
            <Table size="small" aria-label="Archival radial velocity measurements">
              <TableHead>
                <TableRow>
                  <TableCell>Observation</TableCell>
                  <TableCell>MJD</TableCell>
                  <TableCell>RV ± error (km/s)</TableCell>
                  <TableCell>RV screen</TableCell>
                  <TableCell>Spectrum</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {observations.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{surveys[row.survey] || row.survey} {row.obs}</TableCell>
                    <TableCell>{row.mjd?.toFixed(4) ?? "—"}</TableCell>
                    <TableCell>
                      {row.rv_km_s?.toFixed(1) ?? "—"}
                      {row.rv_error_km_s != null && ` ± ${row.rv_error_km_s.toFixed(1)}`}
                    </TableCell>
                    <TableCell>
                      {row.counterpart_check
                        ? "Different counterpart"
                        : row.used_for_rv
                          ? "Pass"
                          : row.rv_km_s != null ? "Excluded" : "—"}
                    </TableCell>
                    <TableCell>
                      {spectra[row.id] ? (
                        <Button onClick={() => setSpectra(({ [row.id]: _, ...rest }) => rest)}>
                          Hide
                        </Button>
                      ) : (
                        <Button disabled={busy || !row.spectrum_available} onClick={() => query(row)}>
                          Load spectrum
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {plot.length > 0 && (
            <Suspense fallback={<CircularProgress size={20} />}>
              <SpectraPlot spectra={plot} />
            </Suspense>
          )}
        </>
      )}
    </Box>
  );
};

export default ArchivalRv;
