export const mockProfiles = [
  {
    key: 'sn_hunter',
    name: 'SN Hunter',
    description: 'Finds peculiar supernovae — 02cx-like, super-Chandrasekhar, unusual decline rates.',
  },
  {
    key: 'rare_transient',
    name: 'Rare Transient',
    description: 'Finds genuinely rare events: TDEs, Kilonovae, FBOTs, Luminous Red Novae.',
  },
  {
    key: 'variable_star',
    name: 'Variable Star',
    description: 'Finds known variable stars behaving in unexpected ways (e.g., period changes).',
  }
];

export const getMockScore = (objectId, profileKey) => {
  // Generate a deterministic but seemingly random anomaly score
  // based on the object ID string and profile key
  const stringToSeed = objectId + profileKey;
  let seed = 0;
  for (let i = 0; i < stringToSeed.length; i++) {
    seed = (seed * 31 + stringToSeed.charCodeAt(i)) % 10000;
  }
  
  // Normalize to 0.0 - 1.0, weighted slightly higher for certain profiles
  let score = seed / 10000.0;
  
  if (profileKey === 'sn_hunter') {
      score = Math.min(0.99, score + 0.2); // SN Hunter is aggressive
  } else if (profileKey === 'variable_star') {
      score = score * 0.7; // Variable is conservative
  }
  
  return score.toFixed(2);
};

export const getMockLLMVerdict = (objectId, profileKey) => {
  // A set of plausible-sounding fake LLM outputs to demonstrate the UX
  const verdicts = {
    'sn_hunter': {
      verdict: 'interesting',
      confidence: 0.85,
      is_candidate: true,
      suggested_class: 'SN Ia-pec',
      reasoning: 'Rapid 3-mag brightening within 5 days. The light curve shape is inconsistent with normal Type Ia templates and lacks a clear secondary peak in the redder bands, suggesting a peculiar subtype.'
    },
    'rare_transient': {
      verdict: 'noise',
      confidence: 0.92,
      is_candidate: false,
      suggested_class: null,
      reasoning: 'This object shows a very faint, single detection followed by nothing. Given the high magnitude error (0.2+ mag) and lack of subsequent detections, this is highly likely to be a subtraction artifact or cosmic ray, not a rare transient.'
    },
    'variable_star': {
      verdict: 'interesting',
      confidence: 0.78,
      is_candidate: true,
      suggested_class: 'RR Lyrae',
      reasoning: 'The object is a known RR Lyrae (based on SIMBAD/ALeRCE cross-match), but the current outburst shows a dramatic 30% phase shift and amplitude increase compared to historical data, typical of the Blazhko effect or a possible mode-switching event.'
    }
  };

  return verdicts[profileKey] || verdicts['sn_hunter'];
};
