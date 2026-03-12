/**
 * Unit tests for EquipmentPickerDrawer.
 * Covers: title, add-form, type-selector UX, increment chips,
 * bodyweight form, and getEquipmentDisplayName helper.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import type { EquipmentProfile } from "../types";

// ---------------------------------------------------------------------------
// Mocks — must be declared before imports
// ---------------------------------------------------------------------------

jest.mock("../../../components/ui/sheet", () => ({
  Sheet: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div data-testid="sheet">{children}</div> : null,
  SheetContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  SheetHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  SheetTitle: ({ children }: { children: React.ReactNode }) => (
    <h2>{children}</h2>
  ),
}));

jest.mock("../../../components/ui/button", () => ({
  Button: ({
    children,
    onClick,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
  }) => <button onClick={onClick}>{children}</button>,
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

jest.mock("../id", () => ({ makeId: () => "new-id" }));

// ---------------------------------------------------------------------------
// Controllable storage mock
// ---------------------------------------------------------------------------

const mockProfiles: EquipmentProfile[] = [];
const mockSaveEquipmentProfile = jest.fn();

jest.mock("../storage", () => ({
  listEquipmentProfiles: () => mockProfiles,
  saveEquipmentProfile: (...args: unknown[]) =>
    mockSaveEquipmentProfile(...args),
  DEFAULT_INCREMENT_BY_TYPE: {
    barbell: 5,
    dumbbell: 5,
    cable_stack: 5,
    machine_plate_loaded: 10,
    machine_selectorized: 10,
    smith: 5,
    bodyweight: 0,
    other: 5,
  },
  EQUIPMENT_TYPE_LABELS: {
    barbell: "Barbell",
    dumbbell: "Dumbbell",
    cable_stack: "Cable",
    machine_plate_loaded: "Plate-Loaded Machine",
    machine_selectorized: "Pin-Loaded Machine",
    smith: "Smith Machine",
    bodyweight: "Bodyweight",
    other: "Other / Custom",
  },
}));

// ---------------------------------------------------------------------------
// Static import of component (must come after mocks)
// ---------------------------------------------------------------------------

import EquipmentPickerDrawer from "../EquipmentPickerDrawer";
import { getEquipmentDisplayName } from "../equipmentDisplay";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BARBELL_PROFILE: EquipmentProfile = {
  id: "eq-1",
  name: "Barbell",
  type: "barbell",
  incrementLb: 5,
  isDefault: true,
};

const DUMBBELL_PROFILE: EquipmentProfile = {
  id: "eq-2",
  name: "Dumbbell",
  type: "dumbbell",
  incrementLb: 5,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setMockProfiles(profiles: EquipmentProfile[]) {
  mockProfiles.length = 0;
  mockProfiles.push(...profiles);
}

function renderDrawer(
  overrides: Partial<{
    selectedId: string;
    profiles: EquipmentProfile[];
  }> = {}
) {
  setMockProfiles(overrides.profiles ?? []);

  const onSelect = jest.fn();
  const onClose = jest.fn();

  render(
    <EquipmentPickerDrawer
      open
      selectedId={overrides.selectedId}
      onSelect={onSelect}
      onClose={onClose}
    />
  );

  return { onSelect, onClose };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockSaveEquipmentProfile.mockClear();
  setMockProfiles([]);
});

// 1. Drawer title is "Select equipment" (not exercise name)
it('picker mode title is "Select equipment"', () => {
  renderDrawer();
  expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
    "Select equipment"
  );
});

// 2. Add form title is "Add equipment"
it('add form title is "Add equipment"', () => {
  renderDrawer();
  fireEvent.click(screen.getByText("+ Add custom"));
  expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
    "Add equipment"
  );
});

// 3. All 8 equipment type buttons rendered in browse mode
it("renders all 8 equipment type buttons in browse mode", () => {
  renderDrawer();
  ["Barbell", "Dumbbell", "Cable", "Smith Machine",
   "Plate-Loaded Machine", "Pin-Loaded Machine", "Bodyweight", "Other / Custom"]
    .forEach((label) => expect(screen.getByText(label)).toBeInTheDocument());
});

// 4. Clicking a type button calls onSelect with matching profile
it("clicking a type button calls onSelect with matching profile", () => {
  const { onSelect } = renderDrawer({ profiles: [BARBELL_PROFILE] });
  fireEvent.click(screen.getByTestId("type-btn-barbell"));
  expect(onSelect).toHaveBeenCalledWith(BARBELL_PROFILE);
});

// 5. List rows do not contain "lb steps" text
it('list rows do not contain "lb steps" text', () => {
  renderDrawer({
    profiles: [BARBELL_PROFILE, DUMBBELL_PROFILE],
  });
  const allText = document.body.textContent ?? "";
  expect(allText).not.toContain("lb steps");
  expect(allText).not.toContain("lb increments");
});

// 6. Clicking a type with no profile auto-creates one and calls onSelect
it("clicking a type with no profile auto-creates one and calls onSelect", () => {
  const { onSelect } = renderDrawer({ profiles: [] });
  fireEvent.click(screen.getByTestId("type-btn-dumbbell"));
  expect(mockSaveEquipmentProfile).toHaveBeenCalled();
  expect(onSelect).toHaveBeenCalled();
});

// 7. Increment chips render in add form for non-bodyweight
it("increment chips render in add form for non-bodyweight type", () => {
  renderDrawer();
  fireEvent.click(screen.getByText("+ Add custom"));
  // Default type is barbell (non-bodyweight) → chips should be visible
  expect(screen.getByTestId("increment-chip-2.5")).toBeInTheDocument();
  expect(screen.getByTestId("increment-chip-5")).toBeInTheDocument();
  expect(screen.getByTestId("increment-chip-10")).toBeInTheDocument();
  expect(screen.getByTestId("increment-chip-25")).toBeInTheDocument();
  expect(screen.getByTestId("increment-chip-45")).toBeInTheDocument();
});

// 8. Clicking increment chip marks it active
it("clicking an increment chip marks it as active", () => {
  renderDrawer();
  fireEvent.click(screen.getByText("+ Add custom"));
  const chip10 = screen.getByTestId("increment-chip-10");
  fireEvent.click(chip10);
  // Active class contains "bg-primary"
  expect(chip10.className).toContain("bg-primary");
});

// 9. Bodyweight type hides increment chips
it("bodyweight type hides increment chips and shows no-increment message", () => {
  renderDrawer();
  fireEvent.click(screen.getByText("+ Add custom"));
  // Switch to Bodyweight type — find button inside the add form (not the type-btn in browse)
  const bodyweightChips = screen.getAllByText("Bodyweight");
  // The one inside the form chips area (not a type-btn)
  fireEvent.click(bodyweightChips[0]);
  // Increment chips should disappear
  expect(screen.queryByTestId("increment-chip-5")).not.toBeInTheDocument();
  // No-increment message appears
  expect(
    screen.getByText("Bodyweight — no increment needed.")
  ).toBeInTheDocument();
});

// 10. Selected type row is highlighted with primary border
it("selected type row is highlighted with primary border", () => {
  renderDrawer({ profiles: [BARBELL_PROFILE], selectedId: "eq-1" });
  const btn = screen.getByTestId("type-btn-barbell");
  expect(btn.className).toContain("border-primary");
});

// ---------------------------------------------------------------------------
// getEquipmentDisplayName tests (pure function)
// ---------------------------------------------------------------------------

// 11. nickname wins over brand+type
it("getEquipmentDisplayName: nickname wins over brand and type", () => {
  const p: EquipmentProfile = {
    id: "x",
    name: "Some Name",
    type: "barbell",
    incrementLb: 5,
    nickname: "My Bar",
    brand: "Rogue",
  };
  expect(getEquipmentDisplayName(p)).toBe("My Bar");
});

// 12. brand+type fallback when no nickname
it("getEquipmentDisplayName: brand \u2022 type when no nickname", () => {
  const p: EquipmentProfile = {
    id: "x",
    name: "Rogue \u2022 Barbell",
    type: "barbell",
    incrementLb: 5,
    brand: "Rogue",
  };
  expect(getEquipmentDisplayName(p)).toBe("Rogue \u2022 Barbell");
});

// 13. type-only when no nickname/brand/name
it("getEquipmentDisplayName: type label when no nickname/brand/name", () => {
  const p: EquipmentProfile = {
    id: "x",
    name: "",
    type: "dumbbell",
    incrementLb: 5,
  };
  expect(getEquipmentDisplayName(p)).toBe("Dumbbell");
});
