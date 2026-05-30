/**
 * Core SkyPortal domain types.
 *
 * Hand-written starter set derived from the API payloads and the existing
 * PropTypes declarations. These are intentionally conservative: fields that
 * are not always present are marked optional. Grow these as more components
 * are migrated -- they are the foundation the rest of the typed code leans on.
 */

export interface User {
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  contact_email?: string | null;
  affiliations?: string[];
}

export interface Profile extends User {
  permissions: string[];
  acls?: string[];
  roles?: string[];
  groups?: Group[];
  preferences?: Record<string, unknown>;
  groupAdmissionRequests?: GroupAdmissionRequest[];
}

export interface Group {
  id: number;
  name: string;
  nickname?: string | null;
  single_user_group?: boolean;
  private?: boolean;
  active?: boolean;
  saved_at?: string;
  saved_by?: User | null;
}

export interface GroupAdmissionRequest {
  id: number;
  group_id: number;
  user_id: number;
  status: "pending" | "accepted" | "declined";
}

export interface Classification {
  id: number;
  classification: string;
  probability?: number | null;
  taxonomy_id?: number;
  author_name?: string;
  created_at?: string;
  groups?: Group[];
  votes?: ClassificationVote[];
}

export interface ClassificationVote {
  id?: number;
  voter_id: number;
  vote: number;
}

export interface Annotation {
  id: number;
  obj_id?: string;
  origin: string;
  // Annotation payloads are free-form key/value data.
  data: Record<string, unknown>;
  author?: { username: string } | null;
  created_at: string;
}

export interface PhotStats {
  peak_mag_global?: number | null;
  peak_mjd_global?: number | null;
  last_detected_mag?: number | null;
  last_detected_mjd?: number | null;
}

export interface PhotometryPoint {
  id: number;
  obj_id?: string;
  mjd: number;
  mag?: number | null;
  magerr?: number | null;
  limiting_mag?: number | null;
  filter?: string;
  instrument_id?: number;
  instrument_name?: string;
  snr?: number | null;
  magsys?: string;
  origin?: string | null;
  ra?: number | null;
  dec?: number | null;
  ra_unc?: number | null;
  dec_unc?: number | null;
  created_at?: string;
  owner?: { username: string };
  streams?: { name: string }[];
  validations?: PhotometryValidation[];
  altdata?: Record<string, unknown> | null;
}

export interface PhotometryValidation {
  validated: boolean | null;
  explanation?: string | null;
  notes?: string | null;
}

export interface Thumbnail {
  id?: number;
  type?: string;
  public_url?: string;
}

export interface Source {
  id: string;
  ra: number;
  dec: number;
  gal_lon?: number;
  gal_lat?: number;
  redshift?: number | null;
  origin?: string | null;
  alias?: string[] | null;
  tns_name?: string | null;
  mpc_name?: string | null;
  host?: { name?: string; [key: string]: unknown } | null;
  host_offset?: number | null;
  annotations?: Annotation[];
  classifications?: Classification[];
  groups?: Group[];
  photstats?: PhotStats[];
  thumbnails?: Thumbnail[];
  tags?: SourceTag[];
  summary_history?: { summary: string | null }[];
  color_magnitude?: unknown[];
  labellers?: User[];
  dm?: number | null;
  t0?: number | null;
}

export interface SourceTag {
  id: number;
  name: string;
  objtagoption_id?: number;
}

export interface Candidate extends Source {
  passing_alert_id?: number;
  passed_at?: string;
}

export interface Instrument {
  id: number;
  name: string;
  type?: string;
  band?: string;
  telescope_id?: number;
  filters?: string[];
}

export interface Telescope {
  id: number;
  name: string;
  nickname?: string;
  lat?: number | null;
  lon?: number | null;
  elevation?: number | null;
  diameter?: number;
  robotic?: boolean;
  fixed_location?: boolean;
  skycam_link?: string | null;
}

export interface Taxonomy {
  id: number;
  name: string;
  hierarchy: Record<string, unknown>;
  version?: string;
  isLatest?: boolean;
}

export interface GcnEvent {
  id?: number;
  dateobs: string;
  localizations?: { id: number; localization_name: string }[];
  tags?: string[];
}

export interface Allocation {
  id: number;
  pi?: string;
  group_id?: number;
  instrument_id?: number;
  group?: Group;
  instrument?: Instrument;
}

/** Generic shape of a SkyPortal API JSON response. */
export interface ApiResponse<T = unknown> {
  status: "success" | "error";
  message?: string;
  data?: T;
}
