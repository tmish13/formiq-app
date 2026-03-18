import React, { useState, useMemo } from "react";
import { Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { EXERCISES, getExercisesForEquipmentType } from "./catalog";
import { EQUIPMENT_TYPE_LABELS } from "./storage";
import type { Exercise, EquipmentType, EquipmentProfile } from "./types";
import type { CustomExercise } from "./storage";

interface ExercisePickerModalProps {
  open: boolean;
  equipmentType?: EquipmentType;
  /** Full equipment profile, needed to filter by custom equipment id. */
  currentEquipment?: EquipmentProfile | null;
  onSelect: (exercise: Exercise) => void;
  onClose: () => void;
  /** User-created custom exercises merged into the search pool. */
  customExercises?: CustomExercise[];
  /** Called when user wants to create a new exercise with the given name. */
  onCreateCustom?: (name: string) => void;
  /** Called when user deletes a custom exercise. */
  onDeleteCustomExercise?: (id: string) => void;
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
  currentEquipment,
  onSelect,
  onClose,
  customExercises = [],
  onCreateCustom,
  onDeleteCustomExercise,
}: ExercisePickerModalProps) {
  const [query, setQuery] = useState("");
  /** id of the exercise pending delete confirmation, or null */
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const isCustomEquipment = currentEquipment?.isCustom === true;

  /**
   * Custom exercises visible for this equipment context:
   * - Custom equipment selected: exercises linked to that equipment id.
   * - Standard/no equipment: exercises without a specific equipment link,
   *   optionally filtered by equipment type.
   */
  const linkedCustomExercises = useMemo(() => {
    if (isCustomEquipment && currentEquipment) {
      return customExercises.filter(
        (e) => e.equipmentId === currentEquipment.id,
      );
    }
    // For standard equipment, show custom exercises that match the type
    // (or have no equipmentId — they're "global" custom exercises)
    if (equipmentType && equipmentType !== "other") {
      return customExercises.filter(
        (e) =>
          !e.equipmentId && e.allowedEquipment.includes(equipmentType),
      );
    }
    return customExercises.filter((e) => !e.equipmentId);
  }, [isCustomEquipment, currentEquipment, customExercises, equipmentType]);

  const catalogPool = useMemo(() => {
    if (equipmentType && equipmentType !== "other") {
      return getExercisesForEquipmentType(equipmentType);
    }
    return EXERCISES;
  }, [equipmentType]);

  /** Full list shown in browse mode (no query). Custom exercises float to top. */
  const basePool = useMemo(
    () => [...linkedCustomExercises, ...catalogPool] as Exercise[],
    [linkedCustomExercises, catalogPool],
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
    setConfirmDeleteId(null);
    onClose();
  }

  function handleCreateCustom() {
    if (!onCreateCustom || !query.trim()) return;
    onCreateCustom(query.trim());
    setQuery("");
    onClose();
  }

  function handleDeleteConfirm(id: string) {
    onDeleteCustomExercise?.(id);
    setConfirmDeleteId(null);
  }

  /** CTA for custom equipment with no linked exercises: use the equipment name directly. */
  function handleUseEquipmentName() {
    if (!onCreateCustom || !currentEquipment) return;
    onCreateCustom(currentEquipment.name);
    setQuery("");
    onClose();
  }

  const showCreateOption = Boolean(onCreateCustom && query.trim());

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) {
          setQuery("");
          setConfirmDeleteId(null);
          onClose();
        }
      }}
    >
      <DialogContent className="max-w-sm w-full p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-4 pt-4 pb-2">
          <DialogTitle className="text-base font-semibold">
            Choose Exercise
          </DialogTitle>
        </DialogHeader>

        {/* Equipment context badge */}
        {isCustomEquipment && currentEquipment ? (
          <div className="px-4 pb-2">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1">
              <span className="text-xs font-semibold text-primary truncate max-w-[180px]">
                {currentEquipment.name}
              </span>
              <span className="text-xs text-muted-foreground shrink-0">
                exercises
              </span>
            </div>
          </div>
        ) : equipmentType && equipmentType !== "other" ? (
          <div className="px-4 pb-2">
            <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3 py-1">
              <span className="text-xs font-semibold text-primary">
                {EQUIPMENT_TYPE_LABELS[equipmentType]}
              </span>
              <span className="text-xs text-muted-foreground">
                exercises only
              </span>
            </div>
          </div>
        ) : null}

        <div className="px-4 pb-2">
          <Input
            placeholder="Search exercises or muscles…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="h-9 text-sm"
          />
        </div>

        {/* Explicit CTA when custom equipment has no linked exercises yet.
            Replaces the old misleading "tap + Add" copy — the button IS the action. */}
        {isCustomEquipment && currentEquipment && linkedCustomExercises.length === 0 && !query.trim() && onCreateCustom && (
          <div className="px-4 pb-4 space-y-2">
            <Button className="w-full" onClick={handleUseEquipmentName}>
              Use &ldquo;{currentEquipment.name}&rdquo;
            </Button>
            <p className="text-xs text-muted-foreground text-center">
              Or search below to pick a different exercise.
            </p>
          </div>
        )}

        <ul className="overflow-y-auto max-h-80 divide-y divide-border">
          {results.length === 0 && (
            <li className="px-4 py-6 text-center space-y-3">
              <p className="text-sm font-medium">No matching exercises</p>
              {showCreateOption ? (
                <button
                  type="button"
                  onClick={handleCreateCustom}
                  className="text-sm text-primary underline underline-offset-2"
                >
                  + Add &ldquo;{query.trim()}&rdquo; as a custom exercise
                </button>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {isCustomEquipment
                    ? "Type a name above to create a custom exercise for this equipment."
                    : equipmentType && equipmentType !== "other"
                    ? `No exercises for ${EQUIPMENT_TYPE_LABELS[equipmentType]}. Search all or type a name to create one.`
                    : "Try a different search term."}
                </p>
              )}
            </li>
          )}

          {results.map((ex) => {
            const isCustomEx = (ex as any).isCustom === true;
            const isConfirming = confirmDeleteId === ex.id;
            const canDelete = isCustomEx && Boolean(onDeleteCustomExercise);

            if (isConfirming) {
              return (
                <li
                  key={ex.id}
                  className="flex items-center gap-2 px-4 py-3 bg-destructive/5"
                >
                  <span className="flex-1 text-sm font-medium text-destructive truncate">
                    Delete &ldquo;{ex.name}&rdquo;?
                  </span>
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(null)}
                    className="text-xs text-muted-foreground hover:text-foreground shrink-0"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteConfirm(ex.id)}
                    className="text-xs font-semibold text-destructive hover:underline shrink-0 ml-1"
                  >
                    Delete
                  </button>
                </li>
              );
            }

            return (
              <li key={ex.id}>
                <div className="flex items-center">
                  <button
                    type="button"
                    className="flex-1 flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors min-w-0"
                    onClick={() => handleSelect(ex)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 min-w-0">
                        <p className="text-sm font-medium truncate">{ex.name}</p>
                        {isCustomEx && (
                          <span className="text-[10px] font-semibold text-primary bg-primary/10 rounded-full px-1.5 py-0.5 shrink-0">
                            Custom
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {ex.primaryMuscles.join(", ")}
                      </p>
                    </div>
                    {ex.movementPattern && !isCustomEx && (
                      <Badge variant="secondary" className="text-xs shrink-0">
                        {MOVEMENT_LABELS[ex.movementPattern] ??
                          ex.movementPattern}
                      </Badge>
                    )}
                  </button>

                  {canDelete && (
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(ex.id)}
                      className="px-3 py-3 text-muted-foreground hover:text-destructive transition-colors shrink-0"
                      aria-label={`Delete ${ex.name}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </li>
            );
          })}

          {/* Create custom option at bottom when results exist */}
          {results.length > 0 && showCreateOption && (
            <li className="px-4 py-3 text-center">
              <button
                type="button"
                onClick={handleCreateCustom}
                className="text-sm text-primary underline underline-offset-2"
              >
                + Add &ldquo;{query.trim()}&rdquo; as a custom exercise
              </button>
            </li>
          )}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
