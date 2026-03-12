/**
 * Offline-first localStorage helpers for Workout Mode.
 * Keys use the "formiq-training-v1:" prefix — never conflicts with existing keys.
 * All reads return [] / null on missing or corrupt data; never throw.
 */

import type {
  WorkoutSession,
  SetLog,
  EquipmentProfile,
  EquipmentType,
  ExerciseId,
  GymChainId,
  Gym,
} from "./types";
import type { NextSessionTarget } from "../../utils/nextSessionTargets";

// ---------------------------------------------------------------------------
// Versioned keys
// ---------------------------------------------------------------------------
const KEYS = {
  sessions: "formiq-training-v1:sessions",
  setLogs: "formiq-training-v1:setLogs",
  equipmentProfiles: "formiq-training-v1:equipmentProfiles",
  nextTargets: "formiq-training-v1:nextTargets",
  gyms: "formiq-training-v1:gyms",
} as const;

const LAST_EQUIP_PREFIX = "formiq-training-v1:lastEquip";
const RECENTS_KEY = "formiq-equipment-recents-v1";

/**
 * Normalize an optional key segment — never writes "undefined" or empty strings.
 * Undefined / null / whitespace-only → "none".
 */
export function keyPart(x?: string | null): string {
  return x && x.trim() ? x.trim() : "none";
}

/**
 * Gym-specific key segment: like keyPart but also maps the "default" gym sentinel
 * to "none" so that `gymId: undefined` and `gymId: "default"` resolve to the same
 * storage bucket.  Call-site normalization — keeps keyPart itself simple.
 */
function gymKeyPart(gymId: string | undefined): string {
  return gymId === "default" ? "none" : keyPart(gymId);
}

function safeStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage ?? null;
}

function readJson<T>(key: string): T[] {
  const store = safeStorage();
  if (!store) return [];
  try {
    const raw = store.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    return [];
  }
}

function writeJson<T>(key: string, data: T[]): void {
  const store = safeStorage();
  if (!store) return;
  try {
    store.setItem(key, JSON.stringify(data));
  } catch {
    // quota exceeded — fail silently
  }
}

// ---------------------------------------------------------------------------
// WorkoutSession
// ---------------------------------------------------------------------------

export function listSessions(limit?: number): WorkoutSession[] {
  const all = readJson<WorkoutSession>(KEYS.sessions).sort(
    (a, b) =>
      new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
  );
  return limit != null ? all.slice(0, limit) : all;
}

export function saveSession(session: WorkoutSession): void {
  const existing = readJson<WorkoutSession>(KEYS.sessions).filter(
    (s) => s.id !== session.id,
  );
  writeJson(KEYS.sessions, [session, ...existing]);
}

export function createSession(
  goal: WorkoutSession["goal"],
  chainId?: GymChainId,
  gymId?: string,
): WorkoutSession {
  const { makeId } = require("./id") as typeof import("./id");
  const session: WorkoutSession = {
    id: makeId(),
    startedAt: new Date().toISOString(),
    goal,
    ...(chainId ? { chainId } : {}),
    ...(gymId ? { gymId } : {}),
  };
  saveSession(session);
  return session;
}

// ---------------------------------------------------------------------------
// SetLog
// ---------------------------------------------------------------------------

export function addSetLog(setLog: SetLog): void {
  const existing = readJson<SetLog>(KEYS.setLogs).filter(
    (s) => s.id !== setLog.id,
  );
  writeJson(KEYS.setLogs, [...existing, setLog]);
}

export function deleteSetLog(id: string): void {
  const existing = readJson<SetLog>(KEYS.setLogs).filter((s) => s.id !== id);
  writeJson(KEYS.setLogs, existing);
}

export function listSetLogsForSession(sessionId: string): SetLog[] {
  return readJson<SetLog>(KEYS.setLogs)
    .filter((s) => s.sessionId === sessionId)
    .sort((a, b) => a.setIndex - b.setIndex);
}

/**
 * Returns the most recent working sets for an exercise across all sessions,
 * optionally filtered by equipmentProfileId.
 */
export function listRecentWorkingSets(
  exerciseId: ExerciseId,
  limit: number,
  equipmentProfileId?: string,
): SetLog[] {
  return readJson<SetLog>(KEYS.setLogs)
    .filter(
      (s) =>
        s.exerciseId === exerciseId &&
        s.setType === "working" &&
        (equipmentProfileId == null ||
          s.equipmentProfileId === equipmentProfileId),
    )
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    )
    .slice(0, limit);
}

// ---------------------------------------------------------------------------
// EquipmentProfile
// ---------------------------------------------------------------------------

/** Increment defaults keyed by EquipmentType. */
export const DEFAULT_INCREMENT_BY_TYPE: Record<EquipmentType, number> = {
  barbell:              10,
  dumbbell:             5,
  cable_stack:          5,
  machine_plate_loaded: 10,
  machine_selectorized: 10,
  smith:                10,
  bodyweight:           0,
  weighted_bodyweight:  5,
  other:                5,
};

/** Human-readable labels for EquipmentType. */
export const EQUIPMENT_TYPE_LABELS: Record<EquipmentType, string> = {
  barbell:              "Barbell",
  dumbbell:             "Dumbbell",
  cable_stack:          "Cable",
  machine_plate_loaded: "Plate-Loaded Machine",
  machine_selectorized: "Pin-Loaded Machine",
  smith:                "Smith Machine",
  bodyweight:           "Bodyweight",
  weighted_bodyweight:  "Weighted Bodyweight",
  other:                "Other (show all)",
};

const SEED_PROFILES: EquipmentProfile[] = [
  { id: "seed-barbell",             name: "Barbell",                type: "barbell",              incrementLb: 10, isDefault: true },
  { id: "seed-dumbbell",            name: "Dumbbell",               type: "dumbbell",             incrementLb: 5 },
  { id: "seed-cable",               name: "Cable",                  type: "cable_stack",          incrementLb: 5 },
  { id: "seed-plate-machine",       name: "Plate-Loaded Machine",   type: "machine_plate_loaded", incrementLb: 10 },
  { id: "seed-smith",               name: "Smith Machine",          type: "smith",                incrementLb: 10 },
  { id: "seed-pin-machine",         name: "Pin-Loaded Machine",     type: "machine_selectorized", incrementLb: 10 },
  { id: "seed-bodyweight",          name: "Bodyweight",             type: "bodyweight",           incrementLb: 0 },
  { id: "seed-weighted-bodyweight", name: "Weighted Bodyweight",    type: "weighted_bodyweight",  incrementLb: 5 },
  { id: "seed-other",               name: "Other (show all)",       type: "other",                incrementLb: 5 },
];

export function upsertEquipmentProfile(profile: EquipmentProfile): void {
  const existing = readJson<EquipmentProfile>(KEYS.equipmentProfiles).filter(
    (p) => p.id !== profile.id,
  );
  writeJson(KEYS.equipmentProfiles, [profile, ...existing]);
}

/** Alias for upsertEquipmentProfile — preferred name in new code. */
export function saveEquipmentProfile(profile: EquipmentProfile): EquipmentProfile {
  upsertEquipmentProfile(profile);
  return profile;
}

export function getEquipmentProfile(id: string): EquipmentProfile | undefined {
  return readJson<EquipmentProfile>(KEYS.equipmentProfiles).find((p) => p.id === id);
}

export function deleteEquipmentProfile(id: string): void {
  const existing = readJson<EquipmentProfile>(KEYS.equipmentProfiles).filter(
    (p) => p.id !== id,
  );
  writeJson(KEYS.equipmentProfiles, existing);
}

/**
 * List equipment profiles.
 * Auto-seeds 5 default profiles when storage is empty.
 * Legacy filters (chainId, exerciseId) still work for backward compat.
 */
export function listEquipmentProfiles(
  chainId?: GymChainId,
  exerciseId?: ExerciseId,
): EquipmentProfile[] {
  let stored = readJson<EquipmentProfile>(KEYS.equipmentProfiles);
  if (stored.length === 0) {
    writeJson(KEYS.equipmentProfiles, SEED_PROFILES);
    stored = SEED_PROFILES;
  }
  return stored.filter(
    (p) =>
      (chainId == null || p.chainId === chainId) &&
      (exerciseId == null || p.exerciseId === exerciseId),
  );
}

// ---------------------------------------------------------------------------
// Next-session targets (FIX 3 — gym-aware key)
// ---------------------------------------------------------------------------

interface NextTargetRecord {
  key: string;
  target: NextSessionTarget;
  savedAt: string;
}

/**
 * Build a collision-free storage key for a next-session target.
 * - With equipment: key is scoped to the equipment profile (gym is implicit).
 * - Without equipment: include gymId so two gyms never share a "none" bucket.
 */
function nextTargetKey(
  exerciseId: string,
  equipmentProfileId: string | undefined,
  gymId: string | undefined,
): string {
  if (equipmentProfileId) {
    return `${keyPart(exerciseId)}:${keyPart(equipmentProfileId)}`;
  }
  return `${keyPart(exerciseId)}:${gymKeyPart(gymId)}:none`;
}

export function saveNextTarget(
  exerciseId: string,
  equipmentProfileId: string | undefined,
  gymId: string | undefined,
  target: NextSessionTarget,
): void {
  const key = nextTargetKey(exerciseId, equipmentProfileId, gymId);
  const existing = readJson<NextTargetRecord>(KEYS.nextTargets).filter(
    (r) => r.key !== key,
  );
  writeJson(KEYS.nextTargets, [
    { key, target, savedAt: new Date().toISOString() },
    ...existing,
  ]);
}

export function getNextTarget(
  exerciseId: string,
  equipmentProfileId: string | undefined,
  gymId: string | undefined,
): NextSessionTarget | null {
  const key = nextTargetKey(exerciseId, equipmentProfileId, gymId);
  const record = readJson<NextTargetRecord>(KEYS.nextTargets).find(
    (r) => r.key === key,
  );
  return record?.target ?? null;
}

// ---------------------------------------------------------------------------
// Gyms (FIX 4 — trim/dedupe on create)
// ---------------------------------------------------------------------------

const DEFAULT_GYM: Gym = { id: "default", name: "Default Gym", isDefault: true };

export function listGyms(): Gym[] {
  const stored = readJson<Gym>(KEYS.gyms);
  const hasDefault = stored.some((g) => g.id === "default");
  if (!hasDefault) {
    return [DEFAULT_GYM, ...stored];
  }
  return stored;
}

export function saveGym(gym: Gym): void {
  const existing = readJson<Gym>(KEYS.gyms).filter((g) => g.id !== gym.id);
  writeJson(KEYS.gyms, [gym, ...existing]);
}

export function deleteGym(id: string): void {
  if (id === "default") return; // never remove the default gym
  const existing = readJson<Gym>(KEYS.gyms).filter((g) => g.id !== id);
  writeJson(KEYS.gyms, existing);
}

/**
 * Find an existing gym by name (case-insensitive, trimmed) or create a new one.
 * Rejects empty names (returns Default Gym as safe fallback).
 * Prevents accidental duplicates like "24 Hour" vs " 24 hour ".
 */
export function findOrCreateGym(name: string): Gym {
  const trimmed = name.trim();
  if (!trimmed) return listGyms()[0] ?? DEFAULT_GYM; // empty → safe fallback

  const gyms = listGyms();
  const existing = gyms.find(
    (g) => g.name.trim().toLowerCase() === trimmed.toLowerCase(),
  );
  if (existing) return existing; // dedup — select the already-existing gym

  const { makeId } = require("./id") as typeof import("./id");
  const newGym: Gym = { id: makeId(), name: trimmed };
  saveGym(newGym);
  return newGym;
}

// ---------------------------------------------------------------------------
// Last-used equipment per (gym, exercise) (FIX 5)
// ---------------------------------------------------------------------------

export function getLastEquipmentForExercise({
  gymId,
  exerciseId,
}: {
  gymId: string | undefined;
  exerciseId: string;
}): string | null {
  const store = safeStorage();
  if (!store) return null;
  try {
    return store.getItem(
      `${LAST_EQUIP_PREFIX}:${gymKeyPart(gymId)}:${keyPart(exerciseId)}`,
    );
  } catch {
    return null;
  }
}

export function setLastEquipmentForExercise({
  gymId,
  exerciseId,
  equipmentProfileId,
}: {
  gymId: string | undefined;
  exerciseId: string;
  equipmentProfileId: string;
}): void {
  const store = safeStorage();
  if (!store) return;
  try {
    store.setItem(
      `${LAST_EQUIP_PREFIX}:${gymKeyPart(gymId)}:${keyPart(exerciseId)}`,
      equipmentProfileId,
    );
  } catch {
    // quota exceeded — fail silently
  }
}

// ---------------------------------------------------------------------------
// Gym-agnostic last-equip helpers (Equipment Context system)
// These use the "default" gym bucket — gym no longer scopes equipment.
// ---------------------------------------------------------------------------

/** Gym-agnostic: last equipment used for an exercise, across all gyms. */
export function getLastEquipment(exerciseId: string): string | null {
  return getLastEquipmentForExercise({ gymId: undefined, exerciseId });
}

/** Gym-agnostic: persist last equipment used for an exercise. */
export function setLastEquipment(
  exerciseId: string,
  equipmentProfileId: string,
): void {
  setLastEquipmentForExercise({
    gymId: undefined,
    exerciseId,
    equipmentProfileId,
  });
}

// ---------------------------------------------------------------------------
// Recently-used equipment profiles (Phase 2)
// ---------------------------------------------------------------------------

/**
 * Returns the most-recently-used equipment profile IDs, most recent first.
 * Reads from a separate versioned key (not mixed with profiles list).
 */
export function getRecentEquipmentProfileIds(limit = 3): string[] {
  const store = safeStorage();
  if (!store) return [];
  try {
    const raw = store.getItem(RECENTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as string[]).slice(0, limit) : [];
  } catch {
    return [];
  }
}

/**
 * Prepend profileId to the recents list, deduplicating and capping at `limit`.
 * Safe if called multiple times with same id (idempotent within a render cycle).
 */
export function pushRecentEquipmentProfileId(id: string, limit = 3): void {
  const store = safeStorage();
  if (!store) return;
  // Read a bit more than limit so we can dedup then trim
  const current = getRecentEquipmentProfileIds(limit + 10);
  const deduped = [id, ...current.filter((x) => x !== id)].slice(0, limit);
  try {
    store.setItem(RECENTS_KEY, JSON.stringify(deduped));
  } catch {
    // quota exceeded — fail silently
  }
}
