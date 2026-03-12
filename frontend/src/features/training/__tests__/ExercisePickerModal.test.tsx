/**
 * ExercisePickerModal — equipment-aware filtering tests.
 *
 * Covers the 6 manual-inspection scenarios:
 *   1. Cable Stack  — barbell-only lifts disappear
 *   2. Smith        — only smith-compatible movements appear
 *   3. Plate-Loaded — hack squat + plate-loaded machines appear; cable excluded
 *   4. Bodyweight   — only bodyweight movements appear
 *   5. "other"      — all 58 exercises shown
 *   6. no prop      — all exercises shown (same as other)
 *
 * Uses the REAL catalog so that allowedEquipment data is exercised end-to-end.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ExercisePickerModal from "../ExercisePickerModal";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock("../../../components/ui/dialog", () => ({
  Dialog: ({
    open,
    children,
    onOpenChange,
  }: {
    open: boolean;
    children: React.ReactNode;
    onOpenChange?: (v: boolean) => void;
  }) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  DialogTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
}));

jest.mock("../../../components/ui/input", () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => (
    <input {...props} />
  ),
}));

jest.mock("../../../components/ui/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => (
    <span>{children}</span>
  ),
}));

jest.mock("../storage", () => ({
  EQUIPMENT_TYPE_LABELS: {
    barbell: "Barbell",
    dumbbell: "Dumbbell",
    cable_stack: "Cable Stack",
    machine_plate_loaded: "Plate-Loaded Machine",
    machine_selectorized: "Selectorized Machine",
    smith: "Smith Machine",
    bodyweight: "Bodyweight",
    other: "Other",
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderModal(
  equipmentType?: React.ComponentProps<typeof ExercisePickerModal>["equipmentType"],
) {
  const onSelect = jest.fn();
  const onClose = jest.fn();
  render(
    <ExercisePickerModal
      open
      equipmentType={equipmentType}
      onSelect={onSelect}
      onClose={onClose}
    />,
  );
  return { onSelect, onClose };
}

function allText() {
  return document.body.textContent ?? "";
}

// ---------------------------------------------------------------------------
// Scenario 1 — Cable Stack
// ---------------------------------------------------------------------------

describe("Scenario 1 — Cable Stack", () => {
  it("shows Cable Curl and Face Pull", () => {
    renderModal("cable_stack");
    expect(screen.getByText("Cable Curl")).toBeInTheDocument();
    expect(screen.getByText("Face Pull")).toBeInTheDocument();
    expect(screen.getByText("Tricep Pushdown")).toBeInTheDocument();
    expect(screen.getByText("Seated Cable Row")).toBeInTheDocument();
  });

  it("excludes barbell-only lifts: Back Squat, Barbell Bench Press, Deadlift", () => {
    renderModal("cable_stack");
    expect(screen.queryByText("Back Squat")).not.toBeInTheDocument();
    expect(screen.queryByText("Barbell Bench Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Deadlift")).not.toBeInTheDocument();
  });

  it("excludes smith-only exercises", () => {
    renderModal("cable_stack");
    expect(screen.queryByText("Smith Machine Bench Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Smith Machine Squat")).not.toBeInTheDocument();
  });

  it("excludes bodyweight-only exercises", () => {
    renderModal("cable_stack");
    expect(screen.queryByText("Pull-Up")).not.toBeInTheDocument();
    expect(screen.queryByText("Push-Up")).not.toBeInTheDocument();
    expect(screen.queryByText("Chin-Up")).not.toBeInTheDocument();
  });

  it('shows "Cable Stack" equipment badge', () => {
    renderModal("cable_stack");
    expect(screen.getByText("Cable Stack")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 2 — Smith Machine
// ---------------------------------------------------------------------------

describe("Scenario 2 — Smith Machine", () => {
  it("shows smith-only exercises", () => {
    renderModal("smith");
    expect(screen.getByText("Smith Machine Bench Press")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Squat")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Shoulder Press")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Romanian Deadlift")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Hip Thrust")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Calf Raise")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Split Squat")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Incline Press")).toBeInTheDocument();
  });

  it("excludes generic barbell lifts not in smith", () => {
    renderModal("smith");
    // barbell_back_squat allowedEquipment: ["barbell"] only
    expect(screen.queryByText("Back Squat")).not.toBeInTheDocument();
    expect(screen.queryByText("Barbell Bench Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Overhead Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Deadlift")).not.toBeInTheDocument();
  });

  it("excludes cable-only exercises", () => {
    renderModal("smith");
    expect(screen.queryByText("Cable Curl")).not.toBeInTheDocument();
    expect(screen.queryByText("Seated Cable Row")).not.toBeInTheDocument();
  });

  it("shows calf_raise (allowed for smith)", () => {
    renderModal("smith");
    expect(screen.getByText("Calf Raise")).toBeInTheDocument();
  });

  it('shows "Smith Machine" equipment badge', () => {
    renderModal("smith");
    expect(screen.getByText("Smith Machine")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 3 — Plate-Loaded Machine
// ---------------------------------------------------------------------------

describe("Scenario 3 — Plate-Loaded Machine", () => {
  it("shows Hack Squat and plate-loaded-specific exercises", () => {
    renderModal("machine_plate_loaded");
    expect(screen.getByText("Hack Squat")).toBeInTheDocument();
    expect(screen.getByText("Plate-Loaded Chest Press")).toBeInTheDocument();
    expect(screen.getByText("Plate-Loaded Row")).toBeInTheDocument();
    expect(screen.getByText("Plate-Loaded Pulldown")).toBeInTheDocument();
  });

  it("shows exercises that have machine_plate_loaded in allowedEquipment (hip_thrust, leg_press)", () => {
    renderModal("machine_plate_loaded");
    expect(screen.getByText("Hip Thrust")).toBeInTheDocument();
    expect(screen.getByText("Leg Press")).toBeInTheDocument();
  });

  it("excludes cable-only exercises", () => {
    renderModal("machine_plate_loaded");
    expect(screen.queryByText("Cable Curl")).not.toBeInTheDocument();
    expect(screen.queryByText("Face Pull")).not.toBeInTheDocument();
    expect(screen.queryByText("Tricep Pushdown")).not.toBeInTheDocument();
  });

  it("excludes barbell-only exercises", () => {
    renderModal("machine_plate_loaded");
    expect(screen.queryByText("Back Squat")).not.toBeInTheDocument();
    expect(screen.queryByText("Barbell Bench Press")).not.toBeInTheDocument();
  });

  it('shows "Plate-Loaded Machine" equipment badge', () => {
    renderModal("machine_plate_loaded");
    expect(screen.getByText("Plate-Loaded Machine")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 4 — Bodyweight
// ---------------------------------------------------------------------------

describe("Scenario 4 — Bodyweight", () => {
  it("shows all 7 bodyweight exercises including new ones", () => {
    renderModal("bodyweight");
    expect(screen.getByText("Pull-Up")).toBeInTheDocument();
    expect(screen.getByText("Dip")).toBeInTheDocument();
    expect(screen.getByText("Chin-Up")).toBeInTheDocument();
    expect(screen.getByText("Push-Up")).toBeInTheDocument();
    expect(screen.getByText("Bodyweight Squat")).toBeInTheDocument();
    expect(screen.getByText("Inverted Row")).toBeInTheDocument();
    expect(screen.getByText("Hanging Leg Raise")).toBeInTheDocument();
  });

  it("shows exercises with bodyweight in allowedEquipment (split_squat, step_up)", () => {
    renderModal("bodyweight");
    expect(screen.getByText("Bulgarian Split Squat")).toBeInTheDocument();
    expect(screen.getByText("Step-Up")).toBeInTheDocument();
  });

  it("excludes machine-only exercises", () => {
    renderModal("bodyweight");
    expect(screen.queryByText("Hack Squat")).not.toBeInTheDocument();
    expect(screen.queryByText("Leg Extension")).not.toBeInTheDocument();
    expect(screen.queryByText("Machine Chest Press")).not.toBeInTheDocument();
  });

  it("excludes cable-only exercises", () => {
    renderModal("bodyweight");
    expect(screen.queryByText("Cable Curl")).not.toBeInTheDocument();
    expect(screen.queryByText("Face Pull")).not.toBeInTheDocument();
  });

  it("excludes barbell-only exercises", () => {
    renderModal("bodyweight");
    expect(screen.queryByText("Back Squat")).not.toBeInTheDocument();
    expect(screen.queryByText("Barbell Bench Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Deadlift")).not.toBeInTheDocument();
  });

  it('shows "Bodyweight" equipment badge', () => {
    renderModal("bodyweight");
    expect(screen.getByText("Bodyweight")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 5 — "other" (show all)
// ---------------------------------------------------------------------------

describe('Scenario 5 — "other" type shows everything', () => {
  it("shows exercises from every category", () => {
    renderModal("other");
    // barbell
    expect(screen.getByText("Back Squat")).toBeInTheDocument();
    // smith
    expect(screen.getByText("Smith Machine Bench Press")).toBeInTheDocument();
    // cable
    expect(screen.getByText("Cable Curl")).toBeInTheDocument();
    // machine
    expect(screen.getByText("Hack Squat")).toBeInTheDocument();
    // bodyweight
    expect(screen.getByText("Pull-Up")).toBeInTheDocument();
    expect(screen.getByText("Chin-Up")).toBeInTheDocument();
    // dumbbell
    expect(screen.getByText("Goblet Squat")).toBeInTheDocument();
  });

  it("does NOT show helper text for other", () => {
    renderModal("other");
    expect(screen.queryByText(/exercises only\./i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Scenario 6 — no equipmentType prop (same as "other")
// ---------------------------------------------------------------------------

describe("Scenario 6 — no equipmentType prop shows all", () => {
  it("shows exercises from every category when prop is omitted", () => {
    renderModal(undefined);
    expect(screen.getByText("Back Squat")).toBeInTheDocument();
    expect(screen.getByText("Cable Curl")).toBeInTheDocument();
    expect(screen.getByText("Hack Squat")).toBeInTheDocument();
    expect(screen.getByText("Pull-Up")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Bench Press")).toBeInTheDocument();
  });

  it("does NOT show helper text when no prop", () => {
    renderModal(undefined);
    expect(screen.queryByText(/exercises only\./i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Helper text behaviour
// ---------------------------------------------------------------------------

describe("Equipment badge — persists during search", () => {
  it("badge remains visible when user types a search query", () => {
    renderModal("cable_stack");
    expect(screen.getByText("Cable Stack")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/search/i), {
      target: { value: "curl" },
    });

    // Badge stays visible during search (always-on)
    expect(screen.getByText("Cable Stack")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });

  it("badge stays visible after clearing the search", () => {
    renderModal("cable_stack");

    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "curl" } });
    fireEvent.change(input, { target: { value: "" } });

    expect(screen.getByText("Cable Stack")).toBeInTheDocument();
    expect(screen.getByText("exercises only")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Search within filtered pool
// ---------------------------------------------------------------------------

describe("Search within filtered pool", () => {
  it('cable_stack + "curl" shows Cable Curl but not Barbell Curl (barbell-only)', () => {
    renderModal("cable_stack");
    fireEvent.change(screen.getByPlaceholderText(/search/i), {
      target: { value: "curl" },
    });
    expect(screen.getByText("Cable Curl")).toBeInTheDocument();
    expect(screen.queryByText("Barbell Curl")).not.toBeInTheDocument();
  });

  it('smith + "press" returns only smith press variants', () => {
    renderModal("smith");
    fireEvent.change(screen.getByPlaceholderText(/search/i), {
      target: { value: "press" },
    });
    expect(screen.getByText("Smith Machine Bench Press")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Incline Press")).toBeInTheDocument();
    expect(screen.getByText("Smith Machine Shoulder Press")).toBeInTheDocument();
    // barbell bench press should NOT appear
    expect(screen.queryByText("Barbell Bench Press")).not.toBeInTheDocument();
  });

  it('bodyweight + "row" shows Inverted Row but not Barbell Row or Seated Cable Row', () => {
    renderModal("bodyweight");
    fireEvent.change(screen.getByPlaceholderText(/search/i), {
      target: { value: "row" },
    });
    expect(screen.getByText("Inverted Row")).toBeInTheDocument();
    expect(screen.queryByText("Barbell Row")).not.toBeInTheDocument();
    expect(screen.queryByText("Seated Cable Row")).not.toBeInTheDocument();
  });

  it("shows 'No matching exercises' when search matches nothing in the filtered pool", () => {
    renderModal("bodyweight");
    fireEvent.change(screen.getByPlaceholderText(/search/i), {
      target: { value: "cable" },
    });
    expect(screen.getByText("No matching exercises")).toBeInTheDocument();
    expect(screen.getByText(/No exercises available for Bodyweight yet/)).toBeInTheDocument();
  });

  it("exercise selection calls onSelect with correct exercise and closes", () => {
    const { onSelect, onClose } = renderModal("cable_stack");
    fireEvent.click(screen.getByText("Cable Curl"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "cable_curl" }),
    );
    expect(onClose).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Dumbbell — spot check
// ---------------------------------------------------------------------------

describe("Dumbbell equipment type", () => {
  it("shows dumbbell-specific exercises including new ones", () => {
    renderModal("dumbbell");
    expect(screen.getByText("Goblet Squat")).toBeInTheDocument();
    expect(screen.getByText("Dumbbell Romanian Deadlift")).toBeInTheDocument();
    expect(screen.getByText("Dumbbell Bench Press")).toBeInTheDocument();
    expect(screen.getByText("Bicep Curl")).toBeInTheDocument();
  });

  it("excludes cable-only and smith-only exercises", () => {
    renderModal("dumbbell");
    expect(screen.queryByText("Cable Curl")).not.toBeInTheDocument();
    expect(screen.queryByText("Smith Machine Bench Press")).not.toBeInTheDocument();
    expect(screen.queryByText("Hack Squat")).not.toBeInTheDocument();
  });

  it("shows exercises shared with barbell (rdl, skullcrusher)", () => {
    renderModal("dumbbell");
    // rdl allowedEquipment: ["barbell", "dumbbell"]
    expect(screen.getByText("Romanian Deadlift")).toBeInTheDocument();
    // skullcrusher allowedEquipment: ["barbell", "dumbbell"]
    expect(screen.getByText("Skull Crusher")).toBeInTheDocument();
  });
});
