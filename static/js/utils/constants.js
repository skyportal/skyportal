const C = 299792.458; // km/s
const PHOT_ZP = 23.9; // AB mag zero point

const BASE_LAYOUT = {
  // base layout for all plotly plots
  automargin: true,
  ticks: "outside",
  nticks: 8,
  ticklen: 12,
  minor: {
    ticks: "outside",
    ticklen: 6,
    tickcolor: "black",
  },
  showline: true,
  titlefont: { size: 18 },
  tickfont: { size: 14 },
};

const LINES = [
  {
    color: "#ff0000",
    name: "H",
    x: [3970, 4102, 4341, 4861, 6563, 10052, 10941, 12822, 18756],
  },
  {
    color: "#002157",
    name: "He I",
    x: [3889, 4471, 5876, 6678, 7065, 10830, 20580],
  },
  {
    color: "#003b99",
    name: "He II",
    x: [3203, 4686, 5411, 6560, 6683, 6891, 8237, 10124],
  },
  {
    color: "#8a2be2",
    name: "C I",
    x: [8335, 9093, 9406, 9658, 10693, 11330, 11754, 14543],
  },
  {
    color: "#570199",
    name: "C II",
    x: [
      3919, 3921, 4267, 5145, 5890, 6578, 7231, 7236, 9234, 9891, 17846, 18905,
    ],
  },
  {
    color: "#a30198",
    name: "C III",
    x: [4647, 4650, 5696, 6742, 8500, 8665, 9711],
  },
  { color: "#ff0073", name: "C IV", x: [4658, 5801, 5812, 7061, 7726, 8859] },
  {
    color: "#01fee1",
    name: "N II",
    x: [3995, 4631, 5005, 5680, 5942, 6482, 6611],
  },
  { color: "#01fe95", name: "N III", x: [4634, 4641, 4687, 5321, 5327, 6467] },
  { color: "#00ff4d", name: "N IV", x: [3479, 3483, 3485, 4058, 6381, 7115] },
  { color: "#22ff00", name: "N V", x: [4604, 4620, 4945] },
  {
    color: "#007236",
    name: "O I",
    x: [6158, 7772, 7774, 7775, 8446, 9263, 11290, 13165],
  },
  { color: "#007236", name: "[O I]", x: [5577, 6300, 6363] },
  {
    color: "#00a64d",
    name: "O II",
    x: [3390, 3377, 3713, 3749, 3954, 3973, 4076, 4349, 4416, 4649, 6641, 6721],
  },
  { color: "#b9d2c5", name: "[O II]", x: [3726, 3729] },
  { color: "#aeefcc", name: "[O III]", x: [4363, 4959, 5007] },
  { color: "#03d063", name: "O V", x: [3145, 4124, 4930, 5598, 6500] },
  { color: "#01e46b", name: "O VI", x: [3811, 3834] },
  { color: "#aba000", name: "Na I", x: [5890, 5896, 8183, 8195] },
  {
    color: "#8c6239",
    name: "Mg I",
    x: [3829, 3832, 3838, 4571, 4703, 5167, 5173, 5184, 5528, 8807],
  },
  {
    color: "#bf874e",
    name: "Mg II",
    x: [
      2796, 2798, 2803, 4481, 7877, 7896, 8214, 8235, 9218, 9244, 9632, 10092,
      10927, 16787,
    ],
  },
  { color: "#6495ed", name: "Si I", x: [10585, 10827, 12032, 15888] },
  { color: "#5674b9", name: "Si II", x: [4128, 4131, 5958, 5979, 6347, 6371] },
  { color: "#ffe4b5", name: "S I", x: [9223, 10457, 13809, 18940, 22694] },
  {
    color: "#a38409",
    name: "S II",
    x: [5433, 5454, 5606, 5640, 5647, 6715, 13529, 14501],
  },
  { color: "#009000", name: "Ca I", x: [19453, 19753] },
  {
    color: "#005050",
    name: "Ca II",
    x: [
      3159, 3180, 3706, 3737, 3934, 3969, 8498, 8542, 8662, 9931, 11839, 11950,
    ],
  },
  { color: "#859797", name: "[Ca II]", x: [7292, 7324] },
  {
    color: "#009090",
    name: "Mn I",
    x: [12900, 13310, 13630, 13859, 15184, 15263],
  },
  { color: "#cd5c5c", name: "Fe I", x: [11973] },
  {
    color: "#f26c4f",
    name: "Fe II",
    x: [4303, 4352, 4515, 4549, 4924, 5018, 5169, 5198, 5235, 5363],
  },
  { color: "#f9917b", name: "Fe III", x: [4397, 4421, 4432, 5129, 5158] },
  {
    color: "#ffe4e1",
    name: "Co II",
    x: [
      15759, 16064, 16361, 17239, 17462, 17772, 21347, 22205, 22497, 23613,
      24596,
    ],
  },
  {
    color: "#a55031",
    name: "WR WN",
    x: [
      4058, 4341, 4537, 4604, 4641, 4686, 4861, 4945, 5411, 5801, 6563, 7109,
      7123, 10124,
    ],
  },
  {
    color: "#b9a44f",
    name: "WR WC/O",
    x: [
      3811, 3834, 3886, 4341, 4472, 4647, 4686, 4861, 5598, 5696, 5801, 5876,
      6563, 6678, 6742, 7065, 7236, 7726, 9711,
    ],
  },
  {
    color: "#8357bd",
    name: "Galaxy",
    x: [
      2025, 2056, 2062, 2066, 2249, 2260, 2343, 2374, 2382, 2576, 2586, 2594,
      2599, 2798, 2852, 3727, 3934, 3969, 4341, 4861, 4959, 5007, 5890, 5896,
      6548, 6563, 6583, 6717, 6731,
    ],
  },
  { color: "#e5806b", name: "Tellurics-1", x: [6867, 6884], fixed: true },
  { color: "#e5806b", name: "Tellurics-2", x: [7594, 7621], fixed: true },
  {
    color: "#6dcff6",
    name: "Sky Lines",
    x: [
      4168, 4917, 4993, 5199, 5577, 5890, 6236, 6300, 6363, 6831, 6863, 6923,
      6949, 7242, 7276, 7316, 7329, 7341, 7359, 7369, 7402, 7437, 7470, 7475,
      7480, 7524, 7570, 7713, 7725, 7749, 7758, 7776, 7781, 7793, 7809, 7821,
      7840, 7853, 7869, 7879, 7889, 7914, 7931, 7947, 7965, 7978, 7993, 8015,
      8026, 8063, 8281, 8286, 8299, 8311, 8346, 8365, 8384, 8399, 8418, 8432,
      8455, 8468, 8496, 8507, 8542, 8552, 8632, 8660, 8665, 8768, 8781, 8795,
      8831, 8854, 8871, 8889, 8907, 8923, 8947, 8961, 8991, 9004, 9040, 9051,
      9093, 9103, 9158,
    ],
    fixed: true,
  },
];

const LOGTYPE_TO_COLOR = {
  Message_robo: "blue",
  Power_robo: "red",
  Weather_robo: "green",
  Data_robo: "orange",
  VIC_robo: "purple",
  TCS_robo: "brown",
  SPEC_robo: "pink",
  Queue_robo: "gray",
  FITS_robo: "cyan",
  Filter_robo: "magenta",
  Control: "yellow",
  Motion_robo: "black",
  BestFocus: "darkblue",
  reset_server: "darkred",
  Other: "darkgreen",
};

const STATUS_COLORS = {
  complete: "success.main",
  "not observed": "darkorange",
  error: "error.main",
  failed: "error.main",
  submitted: "mediumpurple",
  pending: "mediumpurple",
  deleted: "secondary.dark",
};

export { C, PHOT_ZP, BASE_LAYOUT, LINES, LOGTYPE_TO_COLOR, STATUS_COLORS };
