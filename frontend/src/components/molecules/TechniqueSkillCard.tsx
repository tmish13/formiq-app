import React from "react";
import { calculateTechniqueLevels, TechniqueLevels } from "../../utils/formSkills";

const SKILL_LABELS: Array<{
  key: keyof Omit<TechniqueLevels, "overall" | "level">;
  label: string;
}> = [
  { key: "stability",   label: "Torso Stability" },
  { key: "kneeControl", label: "Knee Control"    },
  { key: "depth",       label: "Depth"           },
  { key: "posture",     label: "Posture"         },
];

function SkillBar({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const barColor =
    value >= 85 ? "bg-emerald-500" :
    value >= 75 ? "bg-blue-500" :
    value >= 60 ? "bg-amber-400" :
    "bg-red-400";
  const warn = value < 65;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className={`text-xs font-medium ${warn ? "text-amber-500" : "text-foreground"}`}>
          {value}{warn ? " ⚠" : ""}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

interface TechniqueSkillCardProps {
  namedScores: Record<string, number | null> | null | undefined;
}

export function TechniqueSkillCard({ namedScores }: TechniqueSkillCardProps) {
  const levels = calculateTechniqueLevels(namedScores);
  if (levels.overall === null) return null;

  return (
    <div className="rounded-xl border px-4 py-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Squat Technique</h3>
        {levels.level && (
          <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full">
            {levels.level}
          </span>
        )}
      </div>
      {SKILL_LABELS.map(({ key, label }) => (
        <SkillBar key={key} label={label} value={levels[key]} />
      ))}
    </div>
  );
}
