/**
 * Bottom sheet for selecting or creating an equipment profile.
 * Uses shadcn/ui Sheet (side="bottom").
 *
 * Browse mode: 8-type stacked list (one row per EquipmentType).
 * Selecting a type finds the matching profile or auto-creates one from defaults.
 * Creation form: type chips + increment chips + brand/nickname/notes + Save/Back.
 */
import React, { useState, useEffect } from "react";
import { Check, X } from "lucide-react";
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
} from "./storage";
import { makeId } from "./id";
import type { EquipmentProfile, EquipmentType } from "./types";

interface EquipmentPickerDrawerProps {
  open: boolean;
  selectedId?: string;
  onSelect: (profile: EquipmentProfile | null) => void;
  onClose: () => void;
}

const EQUIPMENT_TYPE_ORDER: EquipmentType[] = [
  "barbell",
  "dumbbell",
  "cable_stack",
  "machine_plate_loaded",
  "machine_selectorized",
  "smith",
  "bodyweight",
  "weighted_bodyweight",
  "other",
];

const QUICK_INCREMENTS = [2.5, 5, 10, 25, 45];

export default function EquipmentPickerDrawer({
  open,
  selectedId,
  onSelect,
  onClose,
}: EquipmentPickerDrawerProps) {
  const [profiles, setProfiles] = useState<EquipmentProfile[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<{
    type: EquipmentType;
    brand: string;
    incrementLb: string;
    notes: string;
    nickname: string;
  }>({
    type: "barbell",
    brand: "",
    incrementLb: String(DEFAULT_INCREMENT_BY_TYPE["barbell"]),
    notes: "",
    nickname: "",
  });

  useEffect(() => {
    if (open) {
      setProfiles(listEquipmentProfiles());
      setCreating(false);
    }
  }, [open]);

  /** Auto-suggest increment when type changes. */
  function handleTypeChange(type: EquipmentType) {
    setForm((f) => ({
      ...f,
      type,
      incrementLb: String(DEFAULT_INCREMENT_BY_TYPE[type]),
    }));
  }

  function handleSelect(p: EquipmentProfile) {
    onSelect(p);
    onClose();
  }

  /** Finds existing profile of this type or auto-creates one. */
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

  function handleSave() {
    let parsed = parseFloat(form.incrementLb);
    if (isNaN(parsed) || parsed < 0) return;
    if (form.type === "bodyweight") parsed = 0;

    const typeLabel = EQUIPMENT_TYPE_LABELS[form.type];
    const name =
      form.nickname.trim() ||
      (form.brand.trim() ? `${form.brand.trim()} \u2022 ${typeLabel}` : typeLabel);

    const profile: EquipmentProfile = {
      id: makeId(),
      name,
      type: form.type,
      incrementLb: parsed,
      brand: form.brand.trim() || undefined,
      notes: form.notes.trim() || undefined,
      nickname: form.nickname.trim() || undefined,
      isDefault: profiles.length === 0,
    };

    saveEquipmentProfile(profile);
    onSelect(profile);
    onClose();
  }

  // Currently selected profile (for type-highlight detection)
  const selectedProfile = selectedId
    ? profiles.find((p) => p.id === selectedId) ?? null
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
              {creating ? "Add equipment" : "Select equipment"}
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
            {/* 9-type stacked list — label only, no implementation-detail subtitles */}
            {EQUIPMENT_TYPE_ORDER.map((type) => {
              const isSelected = selectedProfile?.type === type;
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
                  <span className="flex-1 text-sm font-medium">{EQUIPMENT_TYPE_LABELS[type]}</span>
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
                + Add custom
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4 pb-10">
            {/* Equipment type */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Equipment type
              </label>
              <div className="flex flex-wrap gap-2">
                {EQUIPMENT_TYPE_ORDER.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => handleTypeChange(type)}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      form.type === type
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border hover:bg-muted/50"
                    }`}
                  >
                    {EQUIPMENT_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>
            </div>

            {/* Increment — chips for common values only */}
            {form.type !== "bodyweight" ? (
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                  Weight increment (lb)
                </label>
                <div className="flex flex-wrap gap-2">
                  {QUICK_INCREMENTS.map((v) => (
                    <button
                      key={v}
                      type="button"
                      data-testid={`increment-chip-${v}`}
                      onClick={() => setForm((f) => ({ ...f, incrementLb: String(v) }))}
                      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        form.incrementLb === String(v)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border text-muted-foreground hover:bg-muted/50"
                      }`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Bodyweight — no increment needed.
              </p>
            )}

            {/* Brand (optional) */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Brand (optional)
              </label>
              <Input
                placeholder="e.g. Hammer Strength, Life Fitness"
                value={form.brand}
                onChange={(e) =>
                  setForm((f) => ({ ...f, brand: e.target.value }))
                }
                className="h-9 text-sm"
              />
            </div>

            {/* Nickname (optional) */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Nickname (optional — overrides derived name)
              </label>
              <Input
                placeholder="e.g. Cybex leg press"
                value={form.nickname}
                onChange={(e) =>
                  setForm((f) => ({ ...f, nickname: e.target.value }))
                }
                className="h-9 text-sm"
              />
            </div>

            {/* Notes (optional) */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Notes (optional)
              </label>
              <Input
                placeholder="e.g. selectorized stack, 200 lb max"
                value={form.notes}
                onChange={(e) =>
                  setForm((f) => ({ ...f, notes: e.target.value }))
                }
                className="h-9 text-sm"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCreating(false)}
              >
                Back
              </Button>
              <Button className="flex-1" onClick={handleSave}>
                Save
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
