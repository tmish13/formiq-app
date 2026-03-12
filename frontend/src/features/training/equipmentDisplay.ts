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
