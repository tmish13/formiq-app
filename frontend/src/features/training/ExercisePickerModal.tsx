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

interface ExercisePickerModalProps {
  open: boolean;
  equipmentType?: EquipmentType;
  onSelect: (exercise: Exercise) => void;
  onClose: () => void;
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
}: ExercisePickerModalProps) {
  const [query, setQuery] = useState("");

  const basePool = useMemo(
    () =>
      equipmentType && equipmentType !== "other"
        ? getExercisesForEquipmentType(equipmentType)
        : EXERCISES,
    [equipmentType],
  );

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
            <li className="px-4 py-8 text-center">
              <p className="text-sm font-medium mb-1">No matching exercises</p>
              <p className="text-xs text-muted-foreground">
                {equipmentType && equipmentType !== "other"
                  ? `No exercises available for ${EQUIPMENT_TYPE_LABELS[equipmentType]} yet.`
                  : "Try a different search term."}
              </p>
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
        </ul>
      </DialogContent>
    </Dialog>
  );
}
