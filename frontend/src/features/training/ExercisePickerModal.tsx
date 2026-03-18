import React, { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { EXERCISES, getExercisesForEquipmentType } from "./catalog";
import { EQUIPMENT_TYPE_LABELS } from "./storage";
import type { Exercise, EquipmentType } from "./types";
import type { CustomExercise } from "./storage";

interface ExercisePickerModalProps {
  open: boolean;
  equipmentType?: EquipmentType;
  onSelect: (exercise: Exercise) => void;
  onClose: () => void;
  /** User-created custom exercises merged into the search pool. */
  customExercises?: CustomExercise[];
  /** Called when user wants to create a new exercise with the given name. */
  onCreateCustom?: (name: string) => void;
}

const MOVEMENT_LABELS: Record<string, string> = {
  squat: "Squat",
  hinge: "Hinge",
  horizontal_push: "Push",
  horizontal_pull: "Row",
  vertical_push: "Press",
  vertical_pull: "Pull",
  knee_extension: "Quads",
  knee_flexion: "Hams",
  elbow_flexion: "Biceps",
  elbow_extension: "Triceps",
  hip_extension: "Glutes",
  fly: "Fly",
  shoulder_abduction: "Shoulders",
  shoulder_extension: "Rear Delt",
  plantarflexion: "Calves",
  spinal_flexion: "Abs",
};

export default function ExercisePickerModal({
  open,
  equipmentType,
  onSelect,
  onClose,
  customExercises = [],
  onCreateCustom,
}: ExercisePickerModalProps) {
  const [query, setQuery] = useState("");

  const basePool = useMemo(() => {
    const catalog =
      equipmentType && equipmentType !== "other"
        ? getExercisesForEquipmentType(equipmentType)
        : EXERCISES;
    // Merge custom exercises — filter by equipment type when a specific type is selected
    const custom = (equipmentType && equipmentType !== "other")
      ? customExercises.filter((e) => e.allowedEquipment.includes(equipmentType))
      : customExercises;
    return [...catalog, ...custom] as Exercise[];
  }, [equipmentType, customExercises]);

  const results = useMemo(() => {
    if (!query.trim()) return basePool;
    const q = query.toLowerCase();
    return basePool.filter(
      (e) =>
        e.name.toLowerCase().includes(q) ||
        e.primaryMuscles.some((m) => m.toLowerCase().includes(q)) ||
        (e.movementPattern ?? "").toLowerCase().includes(q),
    );
  }, [query, basePool]);

  function handleSelect(ex: Exercise) {
    onSelect(ex);
    setQuery("");
    onClose();
  }

  function handleCreateCustom() {
    if (!onCreateCustom || !query.trim()) return;
    onCreateCustom(query.trim());
    setQuery("");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-sm w-full p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-4 pt-4 pb-2">
          <DialogTitle className="text-base font-semibold">
            Choose Exercise
          </DialogTitle>
        </DialogHeader>

        {equipmentType && equipmentType !== "other" && (
          <div className="px-4 pb-2">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1">
              <span className="text-xs font-semibold text-primary">
                {EQUIPMENT_TYPE_LABELS[equipmentType]}
              </span>
              <span className="text-xs text-muted-foreground">exercises only</span>
            </div>
          </div>
        )}

        <div className="px-4 pb-2">
          <Input
            placeholder="Search exercises or muscles…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="h-9 text-sm"
          />
        </div>

        <ul className="overflow-y-auto max-h-80 divide-y divide-border">
          {results.length === 0 && (
            <li className="px-4 py-6 text-center space-y-3">
              <p className="text-sm font-medium">No matching exercises</p>
              {onCreateCustom && query.trim() ? (
                <button
                  type="button"
                  onClick={handleCreateCustom}
                  className="text-sm text-primary underline underline-offset-2"
                >
                  + Add "{query.trim()}" as a custom exercise
                </button>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {equipmentType && equipmentType !== "other"
                    ? `No exercises for ${EQUIPMENT_TYPE_LABELS[equipmentType]}. Search all or type a name to create one.`
                    : "Try a different search term."}
                </p>
              )}
            </li>
          )}
          {results.map((ex) => (
            <li key={ex.id}>
              <button
                type="button"
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors"
                onClick={() => handleSelect(ex)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{ex.name}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {ex.primaryMuscles.join(", ")}
                  </p>
                </div>
                {ex.movementPattern && (
                  <Badge variant="secondary" className="text-xs shrink-0">
                    {MOVEMENT_LABELS[ex.movementPattern] ??
                      ex.movementPattern}
                  </Badge>
                )}
              </button>
            </li>
          ))}
          {results.length > 0 && onCreateCustom && query.trim() && (
            <li className="px-4 py-3 text-center">
              <button
                type="button"
                onClick={handleCreateCustom}
                className="text-sm text-primary underline underline-offset-2"
              >
                + Add "{query.trim()}" as a custom exercise
              </button>
            </li>
          )}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
