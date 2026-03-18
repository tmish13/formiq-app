/**
 * Pure util for consistent equipment display names.
 * Single source of truth — use this everywhere names appear in UI.
 */
import type { EquipmentProfile } from "./types";
import { EQUIPMENT_TYPE_LABELS } from "./storage";

/**
 * Returns the best human-readable display name for an equipment profile.
 *
 * Priority:
 * 1. nickname (user-set, explicit preference)
 * 2. `${brand} • ${TypeLabel}` if brand is set
 * 3. `name` field (auto-derived on creation)
 * 4. TypeLabel fallback
 */
export function getEquipmentDisplayName(p: EquipmentProfile): string {
  if (p.nickname?.trim()) return p.nickname.trim();
  if (p.brand?.trim()) {
    const typeLabel = EQUIPMENT_TYPE_LABELS[p.type] ?? p.type;
    return `${p.brand.trim()} \u2022 ${typeLabel}`;
  }
  if (p.name?.trim()) return p.name.trim();
  return EQUIPMENT_TYPE_LABELS[p.type] ?? p.type;
}

/**
 * Compute a human-friendly combined display name for an exercise+equipment pair.
 *
 * Rules:
 * - Standard (non-custom) equipment: return exerciseName unchanged.
 *   The equipment name (Barbell, Cable, etc.) is contextual but not part of the
 *   exercise identity.
 * - Custom/specific equipment: merge intelligently to avoid duplication.
 *   1. Exact match → one copy
 *   2. Exercise name already contains equipment name → exercise name wins
 *   3. Equipment name already contains exercise name → equipment name wins
 *   4. Otherwise → "<equipment> <exercise>"
 *
 * @example
 * // Exact match
 * getResolvedExerciseDisplayName("Hammer Strength Chest Press", "Hammer Strength Chest Press", true)
 * // → "Hammer Strength Chest Press"
 *
 * @example
 * // Equipment adds brand prefix
 * getResolvedExerciseDisplayName("Incline Chest Press", "Hammer Strength", true)
 * // → "Hammer Strength Incline Chest Press"
 *
 * @example
 * // Standard equipment — unchanged
 * getResolvedExerciseDisplayName("Overhead Press", "Barbell", false)
 * // → "Overhead Press"
 */
export function getResolvedExerciseDisplayName(
  exerciseName: string,
  equipmentName: string | null | undefined,
  equipmentIsCustom: boolean,
): string {
  const ex = exerciseName.trim();
  if (!equipmentName?.trim() || !equipmentIsCustom) return ex;

  const eq = equipmentName.trim();
  const eqL = eq.toLowerCase();
  const exL = ex.toLowerCase();

  if (eqL === exL) return eq;
  if (exL.includes(eqL)) return ex;   // exercise already contains equipment name
  if (eqL.includes(exL)) return eq;   // equipment name is the more specific form
  return `${eq} ${ex}`;               // both contribute — prepend equipment brand
}
