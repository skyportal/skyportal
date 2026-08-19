// Component styles centralized for better maintainability
// All inline styles extracted from components

export const blockHeaderStyles = {
  // Button styles
  collapseButton: {
    minWidth: 0,
    padding: 2,
  },

  deleteIcon: {
    color: "red",
    fontSize: "medium",
  },

  // Custom block name styles
  customBlockName: {
    base: {
      fontSize: "1em",
      minWidth: 120,
      textAlign: "center",
      cursor: "default",
      pointerEvents: "auto",
    },

    collapsed: {
      fontSize: "1.1em",
      letterSpacing: "0.03em",
      borderWidth: 2,
      borderStyle: "solid",
    },

    normal: {
      borderWidth: 1,
    },

    edited: {
      cursor: "pointer",
    },
  },

  // Custom block name color variants
  customBlockColors: {
    collapsedNormal: {
      background: "linear-gradient(to right, #dbeafe, #e9d5ff)",
      color: "#1e3a8a",
      borderColor: "#a5b4fc",
      boxShadow: "0 2px 8px 0 rgba(80,120,255,0.08)",
    },

    collapsedEdited: {
      background: "#fef3c7",
      color: "#92400e",
      borderColor: "#fdba74",
      boxShadow: "0 2px 8px 0 rgba(255,180,80,0.13)",
    },

    normalNormal: {
      background: "#eff6ff",
      color: "#1e40af",
      borderColor: "#dbeafe",
    },

    normalEdited: {
      background: "#fef9e7",
      color: "#92400e",
      borderColor: "#fde68a",
    },
  },

  // Edited indicator
  editedIndicator: {
    color: "#ea580c",
    fontWeight: 500,
    fontSize: "0.85em",
    marginLeft: 2,
    background: "rgba(255,237,213,0.7)",
    borderRadius: 4,
    padding: "0 6px",
  },

  // Switch container
  switchContainer: {
    marginLeft: 12,
    pointerEvents: "auto",
    display: "flex",
    alignItems: "center",
  },
};

export const filterBuilderStyles = {
  container: {
    width: "100vw",
    minHeight: "100vh",
    padding: "1rem",
    boxSizing: "border-box",
  },
};
