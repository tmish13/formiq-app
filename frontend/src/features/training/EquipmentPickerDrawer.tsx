/**
 * Bottom sheet for selecting or creating an equipment profile.
 * Uses shadcn/ui Sheet (side="bottom").
 *
 * Browse mode:
 *   - "Your Equipment" section — user-created custom profiles, with delete support.
 *   - Standard types stacked list (one row per EquipmentType).
 *   - "+ Add custom equipment" button.
 *
 * Creation form: equipment name (required) + type chips + increment chips.
 */
import React, { useState, useEffect } from "react";
import { Check, X, Trash2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "../../components/ui/sheet";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  listEquipmentProfiles,
  saveEquipmentProfile,
  DEFAULT_INCREMENT_BY_TYPE,
  EQUIPMENT_TYPE_LABELS,
  createCustomEquipmentProfile,
  deleteCustomEquipmentProfile,
} from "./storage";
import { makeId } from "./id";
import type { EquipmentProfile, EquipmentType } from "./types";

interface EquipmentPickerDrawerProps {
  open: boolean;
  selectedId?: string;
  /**
   * ID of the equipment currently in active use during a workout.
   * Deletion is blocked while a profile is in active use.
   */
  activeEquipmentId?: string;
  onSelect: (profile: EquipmentProfile | null) => void;
  onClose: () => void;
  /** Called after a custom equipment profile has been deleted. */
  onDeleteCustom?: (deletedId: string) => void;
}

/** Types shown in the browse list. "other" is omitted — custom equipment
 * covers that use-case via "+ Add custom equipment". */
const EQUIPMENT_TYPE_ORDER: EquipmentType[] = [
  "barbell",
  "dumbbell",
  "cable_stack",
  "machine_plate_loaded",
  "machine_selectorized",
  "smith",
  "bodyweight",
  "weighted_bodyweight",
];

/** All types available when creating a custom equipment item, including
 * "other" as a valid category (the default for custom gear). */
const CREATION_TYPE_ORDER: EquipmentType[] = [
  ...EQUIPMENT_TYPE_ORDER,
  "other",
];

const QUICK_INCREMENTS = [2.5, 5, 10, 25, 45];

export default function EquipmentPickerDrawer({
  open,
  selectedId,
  activeEquipmentId,
  onSelect,
  onClose,
  onDeleteCustom,
}: EquipmentPickerDrawerProps) {
  // Standard (seed/auto-created) profiles, keyed by type
  const [profiles, setProfiles] = useState<EquipmentProfile[]>([]);
  // User-created custom profiles
  const [customProfiles, setCustomProfiles] = useState<EquipmentProfile[]>([]);

  // Creation form state
  const [creating, setCreating] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customType, setCustomType] = useState<EquipmentType>("other");
  const [customIncrement, setCustomIncrement] = useState<string>(
    String(DEFAULT_INCREMENT_BY_TYPE["other"]),
  );

  // Inline delete confirmation: id being confirmed, or null
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      const all = listEquipmentProfiles();
      setProfiles(all.filter((p) => !p.isCustom));
      setCustomProfiles(all.filter((p) => p.isCustom === true));
      setCreating(false);
      setCustomName("");
      setCustomType("other");
      setCustomIncrement(String(DEFAULT_INCREMENT_BY_TYPE["other"]));
      setConfirmDeleteId(null);
    }
  }, [open]);

  function handleSelect(p: EquipmentProfile) {
    onSelect(p);
    onClose();
  }

  /** Finds existing non-custom profile of this type or auto-creates one. */
  function handleSelectType(type: EquipmentType) {
    const match = profiles.find((p) => p.type === type);
    if (match) {
      handleSelect(match);
      return;
    }
    const newProfile: EquipmentProfile = {
      id: makeId(),
      name: EQUIPMENT_TYPE_LABELS[type],
      type,
      incrementLb: DEFAULT_INCREMENT_BY_TYPE[type],
    };
    saveEquipmentProfile(newProfile);
    handleSelect(newProfile);
  }

  function handleTypeChange(type: EquipmentType) {
    setCustomType(type);
    setCustomIncrement(String(DEFAULT_INCREMENT_BY_TYPE[type]));
  }

  function handleSaveCustom() {
    const name = customName.trim();
    if (!name) return;
    const inc = parseFloat(customIncrement);
    const profile = createCustomEquipmentProfile(
      name,
      customType,
      isNaN(inc) || inc < 0 ? DEFAULT_INCREMENT_BY_TYPE[customType] : inc,
    );
    onSelect(profile);
    onClose();
  }

  function handleDeleteRequest(id: string) {
    // Prevent deletion while the profile is actively in use
    if (id === activeEquipmentId) return;
    setConfirmDeleteId(id);
  }

  function handleDeleteConfirm(id: string) {
    deleteCustomEquipmentProfile(id);
    const all = listEquipmentProfiles();
    setCustomProfiles(all.filter((p) => p.isCustom === true));
    setConfirmDeleteId(null);
    onDeleteCustom?.(id);
  }

  const allProfiles = [...profiles, ...customProfiles];
  const selectedProfile = selectedId
    ? allProfiles.find((p) => p.id === selectedId) ?? null
    : null;

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent
        side="bottom"
        className="rounded-t-xl max-h-[85vh] overflow-y-auto [&>button:first-of-type]:hidden sm:max-w-lg sm:mx-auto sm:inset-x-0 sm:left-1/2 sm:-translate-x-1/2"
      >
        <SheetHeader className="mb-4">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-base">
              {creating ? "Add custom equipment" : "Select equipment"}
            </SheetTitle>
            <button
              type="button"
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-colors"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </SheetHeader>

        {!creating ? (
          <div className="space-y-2 pb-10">
            {/* ── Your Equipment ─────────────────────────────────── */}
            {customProfiles.length > 0 && (
              <>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide px-1 pb-1">
                  Your equipment
                </p>

                {customProfiles.map((p) => {
                  const isSelected = selectedId === p.id;
                  const isActive = activeEquipmentId === p.id;
                  const isConfirming = confirmDeleteId === p.id;

                  if (isConfirming) {
                    return (
                      <div
                        key={p.id}
                        className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3"
                      >
                        <span className="flex-1 text-sm font-medium text-destructive truncate">
                          Delete &ldquo;{p.name}&rdquo;?
                        </span>
                        {isActive ? (
                          <span className="text-xs text-muted-foreground shrink-0">
                            In use — switch first
                          </span>
                        ) : (
                          <div className="flex items-center gap-3 shrink-0">
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(null)}
                              className="text-xs text-muted-foreground hover:text-foreground"
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteConfirm(p.id)}
                              className="text-xs font-semibold text-destructive hover:underline"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  }

                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleSelect(p)}
                      className={`w-full flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                        isSelected
                          ? "border-2 border-primary bg-primary/5"
                          : "border-border hover:bg-muted/50"
                      }`}
                    >
                      <span className="flex-1 text-sm font-medium truncate">
                        {p.name}
                      </span>
                      {isSelected && (
                        <Check size={16} className="text-primary shrink-0" />
                      )}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteRequest(p.id);
                        }}
                        className={`shrink-0 p-1 rounded transition-colors ${
                          isActive
                            ? "text-muted-foreground/30 cursor-not-allowed"
                            : "text-muted-foreground hover:text-destructive"
                        }`}
                        aria-label={`Delete ${p.name}`}
                        title={
                          isActive
                            ? "In use during active workout"
                            : `Delete ${p.name}`
                        }
                        disabled={isActive}
                      >
                        <Trash2 size={14} />
                      </button>
                    </button>
                  );
                })}

                {/* Divider before standard types */}
                <div className="border-t border-border pt-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide px-1 pb-1">
                    Standard
                  </p>
                </div>
              </>
            )}

            {/* ── Standard equipment types ────────────────────────── */}
            {EQUIPMENT_TYPE_ORDER.map((type) => {
              const isSelected = selectedProfile?.type === type && !selectedProfile?.isCustom;
              return (
                <button
                  key={type}
                  type="button"
                  data-testid={`type-btn-${type}`}
                  onClick={() => handleSelectType(type)}
                  className={`w-full flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                    isSelected
                      ? "border-2 border-primary bg-primary/5"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <span className="flex-1 text-sm font-medium">
                    {EQUIPMENT_TYPE_LABELS[type]}
                  </span>
                  {isSelected && (
                    <Check size={16} className="text-primary shrink-0" />
                  )}
                </button>
              );
            })}

            <div className="pt-2">
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setCreating(true)}
              >
                + Add custom equipment
              </Button>
            </div>
          </div>
        ) : (
          /* ── Creation form ──────────────────────────────────────── */
          <div className="space-y-4 pb-10">
            {/* Name — the primary required field */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Equipment name *
              </label>
              <Input
                placeholder="e.g. Hammer Strength Incline Press"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                autoFocus
                className="h-9 text-sm"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && customName.trim()) handleSaveCustom();
                }}
              />
            </div>

            {/* Type chips — optional, defaults to "other" */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Equipment type (optional)
              </label>
              <div className="flex flex-wrap gap-2">
                {CREATION_TYPE_ORDER.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleTypeChange(type)}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      customType === type
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border hover:bg-muted/50"
                    }`}
                  >
                    {/* "Other (show all)" is a browse-mode label; in creation context just "Other" */}
                    {type === "other" ? "Other" : EQUIPMENT_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>
            </div>

            {/* Increment chips — only shown for "Other" type.
                Standard types auto-apply a sensible default; no manual entry needed. */}
            {customType === "other" && (
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Weight increment (lb)
                </label>
                <p className="text-xs text-muted-foreground mb-2">
                  Smallest weight step for this equipment
                </p>
                <div className="flex flex-wrap gap-2">
                  {QUICK_INCREMENTS.map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() =>
                        setCustomIncrement(String(v))
                      }
                      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        customIncrement === String(v)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border text-muted-foreground hover:bg-muted/50"
                      }`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCreating(false)}
              >
                Back
              </Button>
              <Button
                className="flex-1"
                disabled={!customName.trim()}
                onClick={handleSaveCustom}
              >
                Save
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
